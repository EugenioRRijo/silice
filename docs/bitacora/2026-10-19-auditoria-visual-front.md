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
