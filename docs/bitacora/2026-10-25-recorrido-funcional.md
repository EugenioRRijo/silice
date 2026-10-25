# Recorrido funcional de las 22 pantallas (BS-F, 2026-10-25)

**Encargo:** Eugenio pidió «que todas las herramientas funcionen». Es la Tarea 9 de `docs/planes/PLAN_BARRA_SUPERIOR.md`
y el §8.3 del diseño aprobado `docs/especificaciones/2026-10-25-barra-superior-design.md`: en cada una de las 22 pantallas de
`frontend-desktop/src/shell/rutas.ts` se ejecuta la **acción principal** con la cuenta que la puede usar y se comprueba el
**resultado visible**, no solo que la pantalla cargue. Esta bitácora es la **lista de defectos**. No se tocó código de la
aplicación.

## 1. Cómo se repite

```powershell
# requiere la interfaz compilada (frontend-desktop/dist); el modo funcional sirve una COPIA congelada de ella
uv run --active --with playwright python scripts/recorrido_ux_playwright.py --funcional --salida <carpeta-fuera-del-repo>
# opciones: --acciones <otro .toml>  --solo hoja entregar   (la siembra se corre siempre)
```

- **Filas:** `scripts/recorrido_funcional.toml`, una por pantalla (ruta, cuenta, carpeta, proyecto, pasos y lo que debe verse),
  más una fila de **siembra**. El formato está explicado en la cabecera del archivo. Acciones: `llenar`, `elegir`, `pulsar`,
  `marcar`, `subir`, `ir`, `esperar`, `tecla`.
- **Navegación por URL** (`location.hash = '#/<id>'`), nunca por el menú: vale igual con el menú lateral de hoy y con la barra
  superior. Una página por cuenta, sin recargar (el proyecto elegido vive en la memoria de la interfaz, RT-9). La carpeta y el
  proyecto se eligen con los `select` `#selector-caso` y `#selector-proyecto`; si no se ven, se abre el panel
  «Carpeta y proyecto» de la barra (`[aria-controls=panel-carpeta-proyecto]`). La carpeta se confirma contra la API
  (`GET /v1/casos`), no contra lo que muestra el selector (véase D1).
- **Pasa** una fila si se ven todos sus textos esperados (o se bajó el archivo y su SHA-256 está en pantalla) **y** no queda
  ningún aviso de error de Carbon en `main` (`admite_error = true` lo permitiría; ninguna fila lo usa).
- **Salida:** `funcional.json` (por fila: pasos, salida, avisos, errores de consola y de red, carpeta mostrada frente a la de la
  API, segundos), `capturas/NN_<ruta>.png`, `arbol/NN_<ruta>.txt` (árbol ARIA de las filas que fallan), `descargas/`.
  Sale con 1 si falla una fila, la siembra o falta una ruta de `rutas.ts` en el `.toml`.
- **Entorno:** Uvicorn en `127.0.0.1` (puerto libre) con una carpeta de datos TEMPORAL sembrada con la demostración ficticia
  (`start.preparar_demo`: `demo`, `s1`, `ti001`, `of001`, `obra_control`) y las cuentas de `tests/fixtures/sesion_web.py`:
  `admin` (administra), `ana` (arma), `rita` (revisa). Chromium de Playwright sin cabeza; servidor y navegador se cierran por
  su PID. La copia congelada de `dist` evita que otro proceso que recompila la interfaz a mitad del recorrido deje trozos
  perezosos en 404 (pasó en la corrida 2: las pantallas mostraron «No se pudo abrir la pantalla… Recargue la página»).
- **Siembra adicional (toda ficticia):** el administrador guarda la empresa «Contratista Demo, C.A.» (`J-00000000-0`) y genera
  una **clave de firma de prueba** desde el propio equipo; el paquete `.silice` lo **genera «Entregar»** en la misma corrida y
  lo **consume «Revisar un paquete»**. Archivos subidos: el libro limpio de `tests/fixtures/libros_empresa.py`, la tasa del BCV
  `tests/fixtures/bcv/2_1_2c26_smc.xls`, `tests/fixtures/precios_empresa_s1.csv`, y las muestras ficticias
  `data/samples/precios/lista_2026-06-01.csv` y `data/samples/telecom/topologia_ti001.csv` (las que usan
  `tests/fixtures/actualizacion_uc02.py` y `tests/fixtures/caso_ti001.py`). La cláusula de reajuste es la de
  `tests/fixtures/reajuste_pantalla.py`. Ningún libro ni dato real.

## 2. Resultado por pantalla (corrida 5, interfaz compilada el 2026-10-25 15:57:22)

**22 de 22 pasan; la siembra pasa.** Orden de ejecución = orden del `.toml` (hay dependencias: Hoja antes de Entregar,
Entregar antes de Revisar, Actualizar antes de Histórico, Libro antes de Historial).

| # | Pantalla | Cuenta | Carpeta / proyecto | Acción principal | Resultado visible comprobado | s |
|---|---|---|---|---|---|---|
| 1 | `administracion` | admin | (por defecto) | crear la cuenta `func01` con rol arma | «func01» y «Persona Ficticia Uno» en la tabla de cuentas | 4,8 |
| 2 | `indices` | admin | (por defecto) | Leer la tasa del BCV y confirmar | «usd_compra: importada (64 valores)», «usd_venta: importada (64 valores)» | 2,4 |
| 3 | `precios_empresa` | admin | s1 | crear la lista de la empresa con el CSV ficticio | «Lista creada» (10 precios propios) | 2,8 |
| 4 | `acerca` | ana | (por defecto) | ver versión y bases | «Versión», «Al día» | 0,7 |
| 5 | `inicio` | ana | (por defecto) | soltar el libro en «Audite un presupuesto» → «Auditar por mi cuenta» | visor del libro con «Hallazgos (2)» y «Total general» | 1,1 |
| 6 | `catalogo` | ana | demo | buscar «PVC» | `LB-02-TUB` y `DEMO-01-INST` en la tabla | 2,3 |
| 7 | `componer` | ana | demo | componer `FUN-001` con un material y guardar | «Siguiente paso» y, en el catálogo, `FUN-001` con su descripción | 1,6 |
| 8 | `similares` | ana | demo | buscar «instalacion de tuberia PVC» | «3 propuestas, de mayor a menor similitud» con `DEMO-01-INST` | 46,0 |
| 9 | `simulador` | ana | demo | generar la lista simulada (semilla 42) | «Lista simulada» con sus insumos | 0,9 |
| 10 | `escenarios` | ana | demo | escenario «utilidad alta ficticia» con utilidad 0.20 | «Comparación contra el base» con el escenario | 1,0 |
| 11 | `tablero` | ana | demo / caso de demostración | abrir el tablero | «Curva del proyecto», «Partidas que más pesan (Pareto)», «Versiones del presupuesto» | 1,3 |
| 12 | `hoja` | ana | demo / caso de demostración | Parámetros: utilidad 0.12 → «Guardar versión…» con su fuente | «Se guardó la versión DEMO-002», «Versión DEMO-002 · Sin cambios sin guardar» | 2,9 |
| 13 | `entregar` | ana | demo / caso de demostración | generar el paquete firmado de DEMO-002 y descargarlo | «Paquete listo y firmado.»; el `.silice` se bajó y su SHA-256 es el que muestra la pantalla | 2,3 |
| 14 | `actualizacion` | ana | demo | revalorar DEMO-001 con la lista de muestra (versión FUN-02) | «Comparativo por partida», «Informe de auditoría de la versión nueva» | 1,1 |
| 15 | `historico` | ana | demo | filtrar desde hoy | filas de «Cemento Portland» y «Arena lavada» de la revaloración anterior | 0,9 |
| 16 | `elaborar` | ana | ti001 | telecom: extraer el cómputo de la topología TI-001 y elaborar | «Presupuesto elaborado», «Informe de auditoría» | 3,1 |
| 17 | `reajuste` | ana | s1 / Contrato S1 (reajuste) | cláusula, componentes, período y ejecutado ficticios → Calcular | «Escalatoria y comprobación, lado a lado» | 4,1 |
| 18 | `control` | ana | obra_control / OBRA-GENERADA | cambiar el umbral de SPI a 0.85 con su fuente | «1 parámetro(s) cambiado(s).» y «0,85» en la tabla | 3,1 |
| 19 | `existencias` | ana | demo | crear el material `ARE-F01` y registrar una entrada de 25 m³ | fila «ARE-F01 Arena lavada ficticia m³ 25 10 Normal» | 3,2 |
| 20 | `revisar` | rita | (por defecto) | abrir el `.silice` de la fila 13 y guardar el dictamen | «Total recalculado», «Dictamen guardado, atado al SHA-256 de este archivo.» | 1,2 |
| 21 | `libros` | rita | (por defecto) | abrir el libro ficticio | visor con «Hallazgos (2)» y «Total general» | 0,9 |
| 22 | `historial` | rita | (por defecto) | ver la auditoría recién guardada | `libro_plantilla_empresa_ficticio.xlsx` en el historial | 0,6 |

Evidencia: `capturas/NN_<ruta>.png` y la fila correspondiente de `funcional.json` en la carpeta de salida de la corrida.
Ninguna fila tuvo respuestas HTTP 4xx/5xx; las filas 6 y 22 registran errores de consola (D2).

## 3. Defectos, de mayor a menor gravedad

Dueño: **armazón** (se corrige en el plan de la barra), **pantalla** (trabajo propio con TDD y árbitro), **`core/`** (bloqueo
para el tutor; no se toca).

| Id | Gravedad | Dueño | Defecto | Evidencia | Causa probable |
|---|---|---|---|---|---|
| D1 | Alta | armazón | **El selector «Carpeta de trabajo» muestra una carpeta que no es la de la sesión.** Con una instalación nueva, el administrador entra y el selector dice «demo», pero la sesión trabaja en `silice.db`: la importación del BCV (fila 2) se guardó en `silice.db`, no en «demo». Además, elegir «demo» en ese estado no dispara el cambio (el navegador no avisa `change` al elegir la opción que ya se ve), así que la persona no puede pasar a «demo» sin elegir antes otra. | corrida 5, `funcional.json` → `resumen.carpeta_mostrada_distinta`: «administracion (admin): muestra 'demo', la sesión usa 'silice.db'» y lo mismo en `indices`; sonda inicial: con el selector en «demo» la lista de proyectos quedó en «Sin proyecto». A `rita` le pasa igual si entra antes que nadie haya abierto la carpeta por defecto (prueba aparte del visor). | `frontend-desktop/src/shell/Selectores.tsx:26` pone `value={casos.actual.nombre}` pero las opciones (`:30`) son solo `casos.casos`; la carpeta por defecto no está en esa lista hasta que su archivo existe en la carpeta de casos (`operacion/base_datos.py:446`, `listar_casos`, y `api/rutas/casos.py:108`). Falta una opción para la carpeta actual cuando no está en la lista. |
| D2 | Media | pantalla (visor del libro) | **Errores de página del visor Univer:** `[redi]: Cannot find "u4" registered by any injector` se repite (el script guarda los 6 primeros por fila; 24 en una prueba aparte con el visor abierto 10 s) mientras el libro está abierto en «Libro de la empresa» (también cuando se llega desde el Inicio). El visor sí dibuja la hoja y los hallazgos. | corrida 5, filas 6 (`catalogo`, primera de `ana` tras el visor del Inicio) y 22 (`historial`, tras `libros`): `consola` con 6 `pageerror` (el tope que guarda el script). | `frontend-desktop/src/visor/adaptadorUniver.ts:42-45` (`createUniver` con los `presets`): algún complemento del preset de hojas pide un servicio que no se registra. |
| D3 | Media | siembra de la demostración (`start.py`) y texto de `core/` | **«Entregar paquete» no funciona con la demostración recién sembrada:** la versión DEMO-001 dice «Cadena rota en la versión DEMO-001: no tiene eslabón; alguien cambió la base fuera del sistema…» y el botón queda deshabilitado. Se arregla solo al guardar una versión nueva en la Hoja (que sella las anteriores de forma retroactiva); por eso el `.toml` pone Hoja antes de Entregar. | sonda con Entregar como primera acción: aviso de error «Cadena rota…» en pantalla (el script la marca como aviso de error). | `start.py:71-89` (`preparar_demo`) copia bases de antes de la cadena (`tests/fixtures/bases/v0_6_0`) y no llama `core.budget.cadena.sellar_historial` (`core/budget/cadena.py:330`), que nadie expone. El texto «alguien cambió la base fuera del sistema» para una versión sin sellar es de `core/budget/cadena.py:374` y `:378-391` (**`core/`: para el tutor**). |
| D4 | Baja | pantalla (`actualizacion`) | **«Actualizar precios» propone la moneda USD aunque el presupuesto base esté en Bs.** Con `s1` y «Drenaje de la clínica / 001» la revaloración falla: «el proyecto esta en Bs y la version FUN-02 en USD: convierta la version (RF-64)…». El mensaje, además, va sin tildes. | corrida 1, `capturas/14_actualizacion.png` (antes de pasar la fila a `demo`, en USD). | `frontend-desktop/src/paginas/actualizacion/index.tsx:68` (`MONEDA_POR_DEFECTO`, no la del presupuesto elegido). El texto sin tildes es de `core/budget/persistencia.py:177` (**`core/`: para el tutor**). |
| D5 | Baja | pantalla (`similares`) / aplicación | **La primera búsqueda de «Partidas similares» tarda 46-59 s** con solo el esqueleto «Buscando partidas similares»: no dice que está cargando el modelo. | corrida 4: 58,6 s; corrida 5: 46,0 s (las demás filas tardan 0,6-4,8 s). Necesita el modelo `paraphrase-multilingual-MiniLM-L12-v2` en la caché local de Hugging Face (lo estaba). | `aplicacion/similares.py:135` (`proponer_similares`) carga `sentence-transformers` dentro de la petición. |
| D6 | Baja | armazón | **El aviso «Carpeta de trabajo cambiada» se queda en todas las pantallas** hasta que se cierra a mano: aparece en 15 de las 22 capturas, incluidas las filas 7 a 15, en las que no se cambió de carpeta (la última vez fue en la fila 6). | corrida 5, `avisos` de las filas 3 y 6-19. | `frontend-desktop/src/shell/Shell.tsx` (`aviso` del cambio de carpeta: no se limpia al navegar). |
| D7 | Baja | pantalla (`historico`) / API | **Cifras con distinto formato en la misma fila del histórico:** «Ayudante 4,00 → 3» (dos decimales en el precio anterior, ninguno en el nuevo). | sonda de Actualizar + Histórico: árbol ARIA, fila «25/10/2026 Ayudante 4,00 3 -25». | El precio anterior llega como lo guardó la lista base («4.00») y el nuevo como el CSV («3»); la pantalla los muestra tal cual. |

**Observaciones que no son defectos:** (1) en «Revisar un paquete», el paquete firmado por la misma instalación sale
«No verificado: … su clave no está registrada en esta instalación»; es lo previsto (la clave hay que registrarla en
«Empresas registradas») y el recorrido no la registra. (2) El visor del libro tarda unos segundos en dibujar la cuadrícula: la
captura que se toma al ver los hallazgos la muestra gris; 10 s después la hoja está dibujada. (3) Inicio dice «Caso abierto:
silice.db» con la extensión, mientras el selector la oculta («silice»).

**Defecto del propio script (corregido aquí):** `rutas_de_la_interfaz()` dejó de leer las páginas (devolvía 0) cuando
`rutas.ts` ganó el campo `enUnaLinea` entre `titulo` y `seccion`; ahora lee cada campo por su nombre, en cualquier orden.

## 4. Lo que el recorrido no cubre todavía

Cada fila prueba **la acción principal**; no prueba todo lo que la pantalla hace. Quedan sin ejecutar: en Administración, las
pestañas Empresas registradas, Claves de API, Asistente de IA, Accesos e Instalación; en Existencias, «Importar báscula» y
«Pesajes sospechosos»; en la Hoja, las pestañas distintas de Parámetros (espacio, planos DXF/IFC, Excel, conversión de
moneda); en Control de obra, valuaciones, valor ganado y recuperación; en Reajuste, «Guardar el estudio» y su Excel; el
recorrido guiado del Inicio; la verificación «Verificado» de un paquete (exige registrar la clave pública en «Empresas
registradas»). Ninguna pantalla quedó sin ejecutar por falta de datos.
