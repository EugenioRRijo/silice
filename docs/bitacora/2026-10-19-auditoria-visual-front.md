# Auditoría visual del front a 1366×768 (solo lectura)

> **Fecha:** 2026-10-19 · **Quién:** tesis-dd, por encargo de tesis-76 · **Qué se auditó:** `inc/ruta-s2-mig-adm-empresa`
> (tip 3d0effe), `frontend-desktop/dist` ya compilado. Sin ediciones ni commits en esa rama.
> **Cómo:** servidor FastAPI en `127.0.0.1:8123` con datos ficticios en una carpeta temporal (cuentas admin y ana) y
> Chrome headless de perfil propio por CDP, viewport 1366×768. Se midió por página: desborde horizontal, radios de
> esquina, sombras, degradados, familias tipográficas, rayas (—) y errores de consola.
> **Capturas:** `scratchpad/dis/capturas` (admin), `capturas_ana` (ana) y `capturas_lento` (espera de 9 s).

## Resultado global

| Criterio de DESIGN.md | Resultado |
|---|---|
| Sin scroll horizontal a 1366 px | **Cumple** en las 18 páginas (`scrollWidth` = ancho, o 1351 por la barra vertical). |
| Esquinas rectas | **Cumple**. Solo las etiquetas «instalado / no instalado» de Acerca usan 16 px (`cds--tag`, píldora estándar de Carbon; aceptable, se anota). |
| Sin sombras ni degradados | **Cumple**. Las únicas sombras son los bordes internos de las pestañas de Carbon. |
| IBM Plex Sans en todo | **Cumple** (única familia medida). |
| Sin errores de consola | **Cumple** (0 en las 18 páginas). |

## Hallazgos

| # | Gravedad | Página | Hallazgo | Arreglo sugerido |
|---|---|---|---|---|
| V-1 | **Importante** | Catálogo, Histórico | Con el caso demo la API contesta 404 (`/v1/partidas`, `/v1/insumos`, `/v1/cambios-precio`) y la pantalla se queda en **esqueleto de carga para siempre** (a 3,5 s y a 9 s). Falta el estado de error. | Mostrar `AvisoError` con el `detalle` de la API tal cual (regla de DESIGN.md) cuando la carga falle; prueba que simule el 404. |
| V-2 | **Importante** | Acerca de | No sigue el marco de las demás: contenido pegado al menú (x = 256, sin el margen de 16 px de las otras páginas), título sin la clase de `heading-04` y texto con jerga («Versión de pyproject.toml»). | Envolver en el mismo contenedor de página que Inicio/Componer, usar `cds--type-heading-04`, y decir «Versión». |
| V-3 | **Importante** | Libro de la empresa | Sin título de página (no hay `h1`), con una franja blanca superior que ocupa el ancho completo y arranca en x = 256 mientras el contenido arranca en 272. | Agregar `h1 «Libro de la empresa»` y alinear la franja con el margen de la página. |
| V-4 | Importante | Inicio | El bloque «Últimas auditorías guardadas» dice «El historial de auditorías aún no está disponible»: confirma que `/v1/auditorias-libro` no existe en esta rama (H-2 del manual). | Integrar primero `inc/ruta-s4-existencias-react`; después el texto desaparece solo. |
| V-5 | Importante | Componer una partida | Párrafo introductorio con jerga interna («UC-11», «UC-10») y nota «Obligatorio (RF-33)»; etiqueta con raya «Rendimiento — unidades por día». DESIGN.md prohíbe jerga y rayas como adorno. | Reescribir en español llano («Si la partida ya existe, se cargan sus tablas y al guardar se reemplaza su composición»); cambiar la raya por dos puntos. |
| V-6 | Pulido | Varias | Largo de línea incoherente: descripciones de Inicio, Acerca y Libro se cortan a ~540 px; las de Índices, Actualizar precios y Escenarios corren hasta 1080 px. | Un ancho máximo común (`max-inline-size: 70ch`) en la clase de nota de `comun.scss`. |
| V-7 | Pulido | Inicio, Libro, Índices | La zona de soltar archivo tiene mucho alto vacío (96 a 160 px) y el texto queda arriba a la izquierda. | Reducir el alto a lo que pide el texto o centrar el contenido; igual en las tres. |
| V-8 | Pulido | Varias | Títulos desiguales: Catálogo, Histórico, Libro, Acerca, Precios e Índices no tienen `h1` visible o usan otro tamaño que Tablero/Componer/Control (`heading-04`). | Un componente de cabecera de página común con `h1` en `heading-04`. |
| V-9 | Pulido | Administración | Aparecen las pestañas «Empresas registradas» y «Asistente de IA» sin migrar, sin ninguna marca de que siguen en la interfaz clásica. | Rotularlas «(interfaz clásica)» o deshabilitarlas con la nota, como hace el menú. |
| V-10 | Informativo | Todas | La barra de scroll vertical de la página roba 15 px (1351 de 1366) y el cuerpo mide 768 en casi todas porque el contenido cabe. Sin efecto. | Ninguno. |

## Lo que NO se pudo comprobar

- **Montos exactos y colores de variación (IBCS)**: el caso demo no tiene presupuestos ni proyectos, así que Tablero,
  Control, Elaborar, Entregar, Reajuste y el informe de Libro solo se vieron en su estado vacío («Elija un proyecto»,
  «No hay presupuestos guardados»). Esa parte requiere un caso ficticio con datos (ver siguiente paso).
- **Estado con error de API y con sesión expirada**: solo el 404 de V-1; la expiración no se probó.
- **Precios de la empresa** y **Administración, Instalación/Claves**: vistas con la cuenta admin solo en su primera
  pestaña; se capturaron pero no se revisaron una por una.
- **Accesibilidad con teclado y lector de pantalla**: no se hizo.
- **Ancho de 1056 px (menú plegable)**: no se hizo.

## Siguiente paso recomendado

Armar un caso ficticio con un presupuesto guardado y un proyecto (con `scripts/` de datos de prueba de la 1.0.0, no con
libros reales) y repetir las capturas de Tablero, Control, Elaborar, Entregar y Libro con informe; después revisar
V-1, V-2, V-3 y V-5, que son lo único que un usuario nota sin buscar.

---

# Segunda pasada: caso ficticio con datos (mismo día, misma rama 3d0effe)

> **Datos:** caso ficticio en la carpeta temporal (nunca `data/`): línea base civil, `DEMO-001` (4131,10 USD según la
> API), `OBRA-GENERADA` (6 partidas, plan de 10 semanas, 4 valuaciones) y dos libros construidos y ficticios
> (`libro_limpio` y uno con el APU-02 sin equipos). Cuenta `ana` (rol arma). Capturas en `scratchpad/dis/capturas_obra`
> y `capturas_libro`. Servidor propio en `127.0.0.1:8123`, cerrado por su PID al terminar.

## Hallazgos nuevos

| # | Gravedad | Página | Hallazgo | Arreglo sugerido |
|---|---|---|---|---|
| V-11 | **Bloqueante** | Tablero, Control de obra | Con proyectos reales **no cargan ninguno**. El selector de la cabecera guarda el `codigo` que da `/v1/proyectos` (`str(id)`, p. ej. `3`) y las dos páginas lo mandan así (`/v1/tablero?proyecto=3`, `/v1/control/linea-base?proyecto=3`), pero esas rutas buscan por `Proyecto.nombre` (`api/rutas/tablero.py:240`, `api/rutas/control.py:68`). Resultado: 404 y el texto «Ese proyecto no existe en este caso» o «No se pudo cargar la linea base / no_disponible». Entregar y Actualizar sí funcionan porque listan por nombre. | Unificar: o las rutas aceptan el id que el front ya manda, o el front manda el nombre. Prueba de API con un proyecto real que pase por el selector. |
| V-12 | Importante | Control de obra | El error muestra el código crudo `no_disponible` en vez de un mensaje en español. | Traducir el código a frase; mantener el `detalle` de la API cuando exista. |
| V-13 | Importante | Entregar paquete | El total se muestra como **«4131.1 USD»**: sin dos decimales ni separador de miles (DESIGN.md: cifras en centésimas, `tabular-nums`). | Formatear con dos decimales y separador de miles; dejar el exacto en el tooltip accesible. |
| V-14 | Importante | Libro de la empresa | La franja de indicadores (Subtotal, IVA, Total) queda **recortada**: la barra oscura inferior y un resto de otro elemento asoman bajo las tres cifras. Ocupa solo la mitad del ancho y no hay `h1`. | Dar alto propio a la franja o quitar el `overflow`; poner el título arriba (ya en V-3). |
| V-15 | Importante | Libro de la empresa | Rótulo «**Meta** 4358.21» en vez de «Total según Sílice» (DESIGN.md pide rótulos que nombren la cosa) y formatos de número mezclados: indicadores con punto decimal («4203.93») y hallazgos en prosa con formato local («4 331,43 USD»). | Rotular «Total del libro» / «Total según Sílice»; un solo formato numérico en toda la pantalla. |
| V-16 | Informativo | Libro de la empresa | El libro con 3,54 % menos que Sílice se pinta **rojo («desfavorable»)** con triángulo. El spec del Inicio dice que un libro **menor** que Sílice es favorable (verde). Puede ser decisión (subestimar es riesgo), pero contradice el spec. | Confirmar la regla con Eugenio o el tutor; documentarla en la pantalla. |
| V-17 | Pulido | Reajuste de precios | Jerga interna en pantalla: «S1 §8.1», «S1-R14», «I0». Fechas como texto «AAAA-MM-DD» mientras Libro y Componer usan selector de fecha. Formulario muy largo (1469 px). | Español llano; un solo componente de fecha; agrupar con pasos o pestañas. |

## Lo que sí se verificó con datos

- Sin scroll horizontal en Entregar, Reajuste, Elaborar, Actualizar, Escenarios y Libro (con informe): cumple.
- Severidad con ícono y texto («Error», círculo naranja con «!»): cumple. Variación en rojo con triángulo y texto
  «desfavorable» junto al Δ: cumple (IBCS: dos semánticas separadas).
- Montos de los indicadores del Libro como texto exacto (4203.93, 672.63, 4876.56, Δ -154.28): se leen en el DOM.
- Libro limpio: «sin variación» en gris y 0 errores: cumple.

## Lo que sigue sin comprobarse

- Tablero y Control con datos: bloqueados por V-11. Se repiten sobre el SHA corregido que avise tesis-76.
- Elaborar con un resultado calculado, Reajuste con resultado y Entregar generando el paquete (necesita la contraseña de
  la clave de firma): no se ejecutaron.
- El tooltip del valor exacto de los indicadores (no se pasó el ratón).
- 1056 px, teclado y lector de pantalla.
