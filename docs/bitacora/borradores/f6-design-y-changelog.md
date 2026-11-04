# Borrador para T9: enmienda de DESIGN.md y línea del CHANGELOG de F6

> Redactado por Antigravity (Gemini 3.8 Flash High, `agy -p`, 2026-11-04). **Borrador:** describe también T6 y T8, que aún no
> existen; en T9 Claude lo contrasta con lo construido antes de aplicarlo.

### (A) Párrafos de reemplazo e inserciones para [frontend-desktop/DESIGN.md](../../../frontend-desktop/DESIGN.md)

REEMPLAZA (lineas 4-5):
```markdown
THESIS: el libro es la evidencia y la pantalla es una lente forense sobre él. Se rechaza el tablero de tarjetas
con KPI en grande como sustituto de la evidencia, y la hoja escondida detrás de un clic. La Vista general de la
empresa (F6) sí muestra indicadores, pero en el orden de Fiori: primero lo que bloquea, después la cartera por moneda
y cada cifra con su enlace a la obra o al libro que la respalda.
```

REEMPLAZA (lineas 90-90):
```markdown
| **Marca** | `--silice-acento` (ámbar) | raya bajo la barra superior, iniciales de la cuenta |
```

REEMPLAZA (lineas 93-96):
```markdown
- **Selección sobre fondo claro = complementario.** El tamaño de letra vive en Cuenta › Pantalla y tamaño de letra
  (y antes de entrar, en las pantallas sin marco): en ambos el fondo es claro y el acento no llega a 3:1 (WCAG 1.4.11),
  por lo que la raya de la opción activa va en `--silice-complementario` (el servidor lo mide ≥ 4,5:1 sobre el fondo,
  el blanco y el lateral). Nunca queda en el azul de Carbon.
```

REEMPLAZA (lineas 105-107):
```markdown
Una **barra superior** y, debajo, una **barra lateral plana** a la izquierda y el contenido (especificación
`docs/especificaciones/2026-10-26-rediseno-marco-obras-design.md`, enmendada el 2026-11-04; código en `src/marco/`).
La navegación va por **espacios**: la Vista general, cada obra y, para lo que es de toda la empresa, Producción,
Auditoría y Precios; cada uno con una barra con sus secciones o herramientas. Lo que trabaja sobre una obra vive
dentro de la obra. En los textos sigue sin decirse «módulo» ni «área».
```

REEMPLAZA (lineas 109-115):
```markdown
- **Barra superior** (`BarraSuperior.tsx`): 3 rem de alto (sigue la escala de letra), fondo `--silice-marco` con texto
  inverso y raya inferior de 3 px `--silice-acento`; queda fija al desplazar. A la izquierda, la marca «Sílice» (o el
  logo de la empresa), que enlaza a la Vista general (`#/inicio/general`), y al lado el nombre de la carpeta activa.
  Sin migas: la ubicación la dicen la barra lateral, la barra del espacio y el título de la pestaña del navegador
  (`ubicar`). A la derecha el botón **«Buscar… (Ctrl+K)»**, la marca de la demostración y «Recorrido» cuando tocan,
  y el botón de la cuenta (un enlace a `#/cuenta/preferencias` con el círculo de iniciales —primera y última palabra—
  y el nombre de la persona; con letra Grande o Muy grande, solo el círculo, con el mismo nombre accesible; sin letras
  en el nombre, el ícono de persona). El tamaño de letra ya no vive en la barra superior: se ajusta dentro de la Cuenta.
```

REEMPLAZA (lineas 124-127):
```markdown
desplazamiento. **Letra Grande o Muy grande:** filas y títulos se compactan (mixin `con-letra-grande` de `_umbrales.scss`:
filas de 1,5 rem, títulos con menos relleno), Costos y producción se pliega, la zona de obras conserva 10 rem como
mínimo y, si aun así no cabe todo, se desplaza la barra entera. Nada desaparece: lo plegado se abre con un clic. El
tamaño de letra vive en **Cuenta › Pantalla y tamaño de letra** (decisión de Eugenio, 2026-11-04), a un clic del botón
de la persona. Antes de entrar sigue en la cabecera sin marco. La base de 116,6667 % por presbicia no cambia.
```

NUEVO DESPUES DE Cabecera de la obra:
```markdown
### Espacios y barra de espacio

Rediseño F6 (`marco/BarraDeEspacio.tsx`, `marco/espacios.ts`). La navegación se organiza en cuatro espacios enrutados:
**Inicio** (`#/inicio/:vista`), la **obra** (`#/obra/:carpeta/:obraId/:seccion`), los espacios de empresa en **Costos y
producción** (`#/produccion/…`, `#/auditoria/…`, `#/precios/…`) y la **Cuenta** (`#/cuenta/:seccion`). Cada espacio tiene
su propia familia de rutas y una sola ruta canónica por pantalla (`rutaCanonica`).

Debajo de la cabecera de cada espacio va la **barra del espacio** (`BarraDeEspacio.tsx`): un contenedor `<nav>`
accesible con fondo `--cds-layer-01`, divisor inferior de 1 px `--cds-border-subtle` y alto mínimo de 2,5 rem (2 rem con
letra Grande o Muy grande). Pinta pestañas horizontales enrutadas (`<Link>` con `aria-current="page"` en la activa) en
orden de lectura con `Tab`. La pestaña activa lleva una raya inferior de 3 px en `--silice-complementario`. Solo se
muestran las secciones o herramientas usables según los permisos y módulos de la cuenta; una herramienta inaccesible
nunca aparece. En la obra, las secciones con pantallas dependientes ofrecen sus subvistas en la misma barra.
```

NUEVO DESPUES DE Espacios y barra de espacio:
```markdown
### Vista general

Rediseño F6, Tarea 8 (`paginas/inicio/index.tsx`, `marco/EspacioDeInicio.tsx`, ruta `#/inicio/general`). Es la pantalla
de entrada al iniciar sesión, con la pestaña hermana «Pendientes» (`#/inicio/pendientes`) a un clic en la barra del
espacio. Estructura visual en el orden de Fiori:

1. **Lo que bloquea:** primer bloque superior, con las tareas urgentes de la bandeja de pendientes que impiden continuar.
2. **Cartera de obras por moneda:** franja de indicadores Fiori con las cifras servidas por el servidor (`GET /v1/obras/resumen/todas`),
   presentadas estrictamente **separadas por moneda** (Bs y USD; nunca se suman entre monedas). Cada cifra enlaza a la
   obra o al documento que la respalda.
3. **Avance ejecutado contra el plan:** comparación por obra con barras horizontales de variación IBCS.
4. **Últimas auditorías forenses:** accesos directos y estado de los libros revisados recientemente (`UltimasAuditorias`).
5. **Producción de áridos:** estado de existencias de la arenera (`PanelArenera`, visible únicamente con el permiso
   `operar_arenera` y el módulo activo).

Ninguna cifra se inventa ni se calcula en la interfaz; si falta avance se indica «Sin avance» y el fallo de un bloque
no interrumpe la carga de los demás.
```

---

### (B) Línea para [CHANGELOG.md](../../../CHANGELOG.md) bajo `[Sin publicar]` / `### Agregado`

```markdown
- Espacios enrutados y Vista general (rediseño F6): la navegación se organiza en cuatro familias de rutas (`/inicio/:vista`, `/obra/:carpeta/:obraId/:seccion`, `/:espacio/:herramienta` y `/cuenta/:seccion`) con una ruta canónica por pantalla (`marco/espacios.ts`, `rutaCanonica`), redirecciones que conservan la consulta y barra horizontal común (`marco/BarraDeEspacio.tsx`). La lista de obras en la barra lateral pasa a ser plana (sin sub-árbol; zonas Inicio, Obras y Costos y producción). Las siete pantallas dependientes de una obra pasan a ser subvistas de su sección (`tablero` en Resumen, `componer` en Presupuesto, `revisar` y `entregar` en Aprobaciones, `actualizar` en Mercado, y `reajuste` y `escenarios` en Control de obra). El tamaño de letra sale de la barra superior y vive en Cuenta › Pantalla y tamaño de letra (`/cuenta/preferencias`, a un clic del botón de la persona; antes de entrar sigue en la cabecera sin marco); la barra superior queda sin migas, muestra la carpeta activa y enlaza «Sílice» a la Vista general. La aplicación abre en la Vista general (`#/inicio/general`, con la bandeja en `#/inicio/pendientes`), que presenta primero lo que bloquea y después la cartera por moneda servida por el servidor (`GET /v1/obras/resumen/todas`, sin sumar nunca Bs con USD), el avance en barras IBCS, últimas auditorías y arenera. Las 31 pantallas conservan sus permisos y módulos; `core/` sin cambios. Decisiones en `docs/especificaciones/2026-11-04-f6-enmienda.md` y contrato en `docs/especificaciones/2026-11-04-f6a-contrato-de-rutas.md`.
```
