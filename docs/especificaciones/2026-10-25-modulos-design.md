# Sílice por módulos, con un Inicio propio en cada uno: diseño

**Fecha:** 2026-10-25 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (árbol `.worktrees/s2madm`) · **Estado:** PROPUESTO (por aprobar por Eugenio).
**Origen:** sesión de diseño con Eugenio del 2026-10-25 (skills impeccable y taste; maquetas en el compañero visual:
`inicio-dashboard-v2.html` y `modulos-v2.html`). Se construye sobre la barra superior ya hecha
(`2026-10-25-barra-superior-design.md`) y encaja con `2026-10-25-montar-presupuesto-design.md`.

## 1. Intención

Eugenio: las herramientas principales del núcleo de la tesis no deben competir en un mismo tablero; deben funcionar como los
**modos de Delta Force**: un menú a la izquierda con los grandes modos y, al elegir uno, **se carga otro módulo completo**, con su
propio inicio, su propia barra de arriba y sus propias pantallas. Además pidió un **tablero detallado** (obras vivas, pendientes por
aprobar y recomendaciones) y que la persona trabaje con sus **obras**, no con «carpetas».

Decisiones de Eugenio en esta sesión:
- **Selector de módulos en un sidebar, estado 3** de la maqueta: **oculto por omisión**; se abre **encima del contenido** con el
  botón «Sílice» (arriba a la izquierda) o con **Esc**; al elegir un módulo se carga y el sidebar se vuelve a ocultar; **«Fijar»** lo
  deja visible siempre (y «Ocultar» lo devuelve al estado oculto).
- **Inicio de «Presupuestos y obras» = opción B (mesa de control)**: cifras Fiori arriba, obras con su avance, columna de pendientes.
- **Mis obras y carpeta oculta**: la persona ve y crea obras; la carpeta de trabajo queda para el administrador.
- **Recomendaciones**: retrasos y compras, precios, aprobaciones y calidad del presupuesto.

## 2. Metas, no-metas y anti-metas

**Metas**
1. Tres **módulos** con identidad propia: **Auditoría**, **Presupuestos y obras**, **Producción**.
2. **Sidebar de módulos** (estado 3) con «Fijar/Ocultar» recordado por cuenta.
3. **Barra superior por módulo**: muestra solo las áreas del módulo abierto, con el nombre del módulo a la izquierda.
4. **Inicio por módulo**: cada módulo arranca en su propio inicio.
5. **Obra en vez de carpeta** en la barra; la carpeta se administra aparte.

**No-metas:** cambiar las direcciones de las pantallas existentes (siguen en `#/<id>`), tema oscuro de la aplicación, pantallas
nuevas que no estén ya en este diseño o en el de «montar un presupuesto».

**Anti-metas:** que cambiar de módulo pierda trabajo sin avisar; que una pantalla quede inalcanzable para un rol que hoy la usa;
un tablero de cifras grandes sin meta ni desviación (Fiori: valor, meta, desviación siempre juntos); cifras inventadas; animación
decorativa; que el sidebar tape el contenido cuando está fijado (fijado empuja, no tapa).

## 3. Los módulos

| Módulo | Para qué (línea del sidebar) | Áreas de su barra | Pantallas |
|---|---|---|---|
| **Auditoría** | Revise presupuestos propios o de terceros | Inicio · Auditar · Paquetes · Historial | Inicio de auditoría; Auditar un presupuesto (`libros`); Revisar un paquete (`revisar`); Historial de auditorías (`historial`) |
| **Presupuestos y obras** | Arme, apruebe y controle sus obras | Inicio · Obras · Partidas · Mercado · Aprobaciones · Control | Inicio (mesa de control); Obras: Hoja (`hoja`), Elaborar (`elaborar`), Tablero (`tablero`), Entregar (`entregar`); Partidas: Componer (`componer`), Catálogo (`catalogo`), Similares (`similares`); Mercado: Estudio de mercado (MP-5), Precios de la empresa (`precios_empresa`), Actualizar precios (`actualizacion`), Histórico (`historico`), Índices del BCV (`indices`), Simulador (`simulador`); Aprobaciones (MP-4); Control: Control de obra (`control`, con procura MP-7), Reajuste (`reajuste`), Escenarios (`escenarios`) |
| **Producción** | Existencias y báscula de la arenera | Inicio · Existencias | Inicio de producción; Existencias de la arenera (`existencias`) |
| *(fuera de los módulos)* | | | Administración (`administracion`) y Acerca de Sílice (`acerca`), al pie del sidebar |

- Un área con varias pantallas abre su **panel de área** (el de la barra ya construida); con una sola, es enlace directo.
- **Visibilidad por rol:** un módulo aparece si la cuenta puede usar al menos una de sus pantallas (mismas acciones que hoy, sin
  cambiar permisos). Quien solo revisa ve Auditoría y, dentro de Presupuestos y obras, Aprobaciones; el administrador ve lo suyo y
  Administración.
- **Dirección:** las pantallas conservan su ruta `#/<id>`; el módulo se deduce de la pantalla. Cada módulo gana su inicio:
  `#/auditoria`, `#/obras`, `#/produccion` (el actual `#/inicio` redirige al inicio del último módulo usado).
- **Último módulo**: Sílice recuerda por cuenta el último módulo abierto y vuelve a él al entrar.

## 4. Sidebar de módulos (estado 3)

- **Botón «Sílice»** (ícono de menú + nombre) en la esquina de la barra; abre/cierra el sidebar. **Esc** lo abre cuando no hay un
  panel, diálogo ni campo de texto con el foco (Esc sigue cerrando primero lo que esté abierto; nunca roba Esc a un formulario).
- **Oculto (por omisión)**: al abrirse aparece encima del contenido con una capa que oscurece el resto; foco atrapado en el sidebar;
  Esc o clic fuera lo cierran y devuelven el foco al botón; elegir un módulo lo carga y cierra el sidebar.
- **Fijado**: franja de 264 px a la izquierda que **empuja** el contenido (no lo tapa); «Ocultar» al pie lo devuelve al estado oculto.
  Por debajo de los umbrales de `_umbrales.scss` (ancho estrecho o letra grande) el estado fijado se comporta como oculto.
- **Contenido**: título «Módulos»; un renglón grande por módulo (nombre en `heading-03`, línea de qué hace en `helper-text`), el
  activo con la barra azul de selección; al pie, Administración, Acerca de Sílice y «Fijar»/«Ocultar».
- **Cambiar de módulo con trabajo sin guardar** (un borrador de la Hoja, un formulario de Componer a medio llenar) pide confirmación,
  con el mismo mecanismo que MP-2 usa al cambiar de carpeta.
- **Preferencia** fijado/oculto y último módulo: por cuenta en el servidor (la misma tabla de elección de MP-2 en `instalacion.db`).
- Estilo: superficie `$background-inverse` (oscura) de Carbon, texto `$text-inverse`, sin animación de entrada, esquinas rectas.

## 5. Barra superior por módulo

- Izquierda: botón «Sílice» y el **nombre del módulo** abierto. Centro: las áreas del módulo (tabla de §3). Derecha: **Obra**
  (selector de obra, en Presupuestos y obras; ver §7), tamaño de letra, cuenta.
- Se reutiliza la barra construida (`BarraSuperior`, `navegacion`): `navegacion` gana el módulo como entrada y devuelve solo sus
  áreas; el registro de páginas (`rutas.ts`) gana a qué módulo y área pertenece cada pantalla (reemplaza a `AREAS`).

## 6. Inicio de cada módulo

- **Presupuestos y obras — mesa de control (opción B)**:
  - **Cifras Fiori** arriba (valor, meta y desviación juntos): monto en ejecución contra lo contratado (versiones aprobadas con línea
    base); avance contra el plan (SPI de las obras en ejecución, con su desviación favorable/desfavorable IBCS y los días); por
    aprobar (cuántas versiones, y la más antigua).
  - **Obras** (tabla Carbon `sm`): obra, etapa (en elaboración, en aprobación, aprobada, en ejecución, atrasada), avance (real de
    plan), total, **qué pasa** con su causa (de MP-7) y el **siguiente paso** como botón (lo bueno de la opción A).
  - **Pendientes** (columna de 380 px): agrupados en Aprobar, Compras, Precios y Calidad; cada uno dice la obra y lleva su acción.
    Reglas deterministas, sin IA: aprobar = versiones en aprobación/devueltas/aprobadas sin entregar (MP-4); compras = pedir antes de
    la fecha, llegó tarde (MP-7c); precios = más de 90 días, sin referencia, partida por debajo del costo frente al mercado (MP-5);
    calidad = hallazgos ERROR/CRÍTICO abiertos, cantidades sin cálculo (MP-3), lista vieja en una obra.
  - **«Nueva obra»** como acción principal del inicio.
  - **Estados**: sin obras (vacío que enseña: «Cree su primera obra» y «Probar con datos de demostración»); cargando (esqueleto con la
    forma final); error (aviso en línea). Mientras una fuente aún no exista (p. ej. antes de MP-7), su grupo de pendientes no se
    muestra (nunca un grupo vacío falso).
- **Auditoría**: el inicio actual de auditar (soltar el Excel y últimas auditorías guardadas), que luego evoluciona con la Fase 1
  «Auditar un presupuesto».
- **Producción**: el panel de la arenera actual (lo que requiere atención y existencias).

## 7. Obra en vez de carpeta

- En Presupuestos y obras, la barra muestra **«Obra: <nombre>»** (o «Todas las obras» en el inicio). Elegir obra es un selector con
  búsqueda; «Nueva obra» crea una (el diálogo de BCP-6 renombrado: nombre, cliente, ubicación, tipo de obra; la moneda es la de la
  carpeta, D-MP1).
- **Una carpeta de la empresa por instalación** para el trabajo diario. Las demás carpetas (la demostración, otra empresa) se
  administran en **Administración › Carpetas de trabajo** (BCP-5 se ubica ahí) y en «Probar con datos de demostración», que abre la
  carpeta de demostración rotulada como tal en la barra («Demostración»).
- Esto **reemplaza** en MP-2 el panel «Carpeta y proyecto» de la barra: queda el selector de obra para todos y la gestión de carpetas
  para el administrador.

## 8. Encaje con «montar un presupuesto»

- MP-5 «Estudio de mercado» va en el área **Mercado** y MP-4 «Aprobaciones» en el área **Aprobaciones** de Presupuestos y obras.
- MP-2 cambia según §7. El inicio B consume los datos de MP-4, MP-5 y MP-7 a medida que existan.
- **Orden**: primero el armazón de módulos (MOD-1 a MOD-3), después el plan de «montar un presupuesto» con estas ubicaciones, y el
  inicio B (MOD-4) crece con cada pieza.

## 9. Pruebas y aceptación

TDD con rojo visto; la navegación por módulo con oráculos a mano (qué módulos y áreas ve cada rol); sidebar: abrir con botón y con
Esc, Esc no roba el foco a un campo, foco atrapado y devuelto, fijar/ocultar recordado, fijado empuja el contenido, confirmación al
cambiar de módulo con trabajo sin guardar; recorrido visual con Playwright (tres letras, 1366 y 1056 px, sidebar oculto/abierto/
fijado) y recorrido funcional (22 pantallas alcanzables por su módulo); revisor de diseño con impeccable (crítica y pulido) sobre
las capturas.

## 10. Rebanadas

| Rebanada | Hace | Depende de |
|---|---|---|
| MOD-1 | Registro de módulos y áreas en `rutas.ts`; `navegacion` por módulo; rutas de inicio por módulo; último módulo recordado | — |
| MOD-2 | Sidebar de módulos (estado 3), botón «Sílice», Esc, fijar/ocultar recordado, confirmación al salir con trabajo sin guardar | MOD-1 |
| MOD-3 | Barra superior por módulo; selector de obra en lugar de carpeta y proyecto; carpetas en Administración | MOD-1, MP-2 |
| MOD-4 | Inicio de Presupuestos y obras (mesa de control B) con lo que ya existe; crece con MP-4, MP-5 y MP-7 | MOD-3 |
| MOD-5 | Pulido de diseño con impeccable (critique y polish), recorridos visual y funcional, manual | todas |

## 11. Decisiones de ingeniería tomadas aquí (las ratifica Eugenio al leer)

1. Las rutas `#/<id>` no cambian; el módulo se deduce de la pantalla; se agregan `#/auditoria`, `#/obras`, `#/produccion`.
2. Administración y Acerca quedan fuera de los módulos, al pie del sidebar.
3. Esc abre el sidebar solo si no hay nada abierto ni un campo con el foco.
4. El estado fijado se desactiva por debajo de los umbrales de ancho y letra (se comporta como oculto).
5. Preferencias (fijado, último módulo) por cuenta en `instalacion.db`, junto a la elección de obra de MP-2.
