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

---

# Tercera pasada: SHA 01da0d1 (inc/ruta-s2-mig-adm-empresa), mismos datos ficticios

> Servidor propio en `127.0.0.1:8123` contra `.worktrees/s2madm`, cerrado por su PID. Capturas en
> `scratchpad/dis/capturas_v2` y `capturas_libro2`. Sin scroll horizontal en las 11 páginas medidas ni en el Libro.

## Cerrados

| # | Estado |
|---|---|
| V-11 | **Cerrado.** Tablero y Control cargan `DEMO-001` y `OBRA-GENERADA`; las peticiones ya no dan 404. |
| V-12 | Cerrado en lo visto: Control ya no muestra `no_disponible`. |
| V-13 | **Cerrado.** Entregar muestra «4.131,10 USD» (es-VE) y el exacto visible: «Valor exacto: 4131.095741666666666666666665 USD». |
| V-2, V-3, V-14 | **Cerrados.** Acerca de tiene título y «Versión»; Libro de la empresa tiene `h1`, indicadores sin recorte, severidad con ícono y pestañas con su marca de hallazgos. |
| V-5 | Cerrado: Componer sin «UC-10», «UC-11» ni «RF-33» y sin raya. |
| V-15 | **Parcial.** El formato es único (es-VE: 4.203,93 y los hallazgos en prosa también), pero el rótulo sigue siendo **«Meta»**, no «Total según Sílice». |
| V-1 | **Parcial.** Ya hay estado de error («No se pudo cargar el catálogo»), pero ver V-18: el error es real y permanente. |

## Hallazgos nuevos

| # | Gravedad | Página | Hallazgo | Arreglo sugerido |
|---|---|---|---|---|
| V-18 | **Bloqueante** | Catálogo, Histórico | Siguen **sin funcionar**: el front pide `/v1/partidas`, `/v1/insumos` y `/v1/cambios-precio`, pero la API sirve esas rutas **sin prefijo** (`/partidas`, `/insumos`, `/cambios-precio`, según `openapi.json`). 404 «Not Found» siempre. Las rutas están en `api/rutas/catalogo.py` y `listas.py`, montadas con `app.include_router(catalogo.router)` sin `/v1`. | Alinear el prefijo: o la API monta esas rutas también bajo `/v1`, o el front llama las rutas existentes. Prueba de API que recorra el cliente real de cada página. |
| V-19 | Importante | Tablero | Formato numérico **distinto al de Entregar y Libro**: montos como «95066.60 USD», «4131.10 USD» y filas de tablas «2258.98 USD» (punto, sin miles); ejes de los gráficos en estilo inglés («4,131», «1,000»). No hay el exacto accesible. | Usar el mismo formateador es-VE de Entregar/Libro y poner el exacto en el `title`. |
| V-20 | Importante | Tablero | Textos **sin tildes**: «Version», «Auditoria», «Dia 1», «Aun no hay control de obra», «Sin linea base». DESIGN.md pide ortografía correcta. | Revisar los textos de `tablero` y `control` y acentuarlos. |
| V-21 | Importante | Tablero | Tres **donas** muestran avance, SPI y CPI como partes de un todo (por ejemplo SPI 0,98 = «97,8 % / 2,2 %»), en verde azulado y **morado**. Un índice no es una proporción, y DESIGN.md reserva el morado para atípicos. Repiten además los indicadores de debajo. | Quitar las donas o reemplazar por tarjetas con valor, meta y desviación (Fiori/IBCS); sin morado. |
| V-22 | Importante | Control de obra | Se ven los identificadores internos: `spi_error`, `cpi_error`, `SUPUESTO_DECLARADO`, `DATO_DEL_CONTRATO`, «AL-1»… «AL-5», «eta». Textos sin tildes («Linea base vigente», «Parametros», «penalizacion») aunque la pestaña sí dice «Línea base». | Mostrar nombres en español («Umbral de SPI», «Supuesto declarado») y acentuar. |
| V-23 | Pulido | Inicio | Muestra «Proyecto: 2» (el número) en vez del nombre. Sigue el 404 de `/v1/auditorias-libro` y `/v1/produccion/existencias` (V-4). | Mostrar el nombre del proyecto; V-4 queda hasta integrar la arenera. |
| V-24 | Pulido | Libro de la empresa | El rótulo «Meta» (V-15), y los controles «Fecha de devolución / Cambiar libro» quedaron **en la barra superior** junto a Caso y Proyecto, mezclados con los de la cabecera. | Llevarlos a la propia página, bajo el título. |
| V-25 | Informativo | Tablero | Las sombras y radios medidos (2 px, `0 0 0 2px`, sombra 6 px) son de los `checkbox` y la etiqueta del umbral de los gráficos de Carbon Charts, no de tarjetas. | Ninguno. |

## Sigue sin comprobarse

- Entregar generando el paquete (clave de firma), Elaborar y Reajuste con resultado, el tooltip del exacto, 1056 px,
  teclado y lector de pantalla.
- V-16 (libro menor que Sílice en rojo) sigue como decisión de Eugenio o del tutor: en esta pasada se ve igual.
