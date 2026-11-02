# Recorrido funcional de las 22 pantallas (BS-F, 2026-10-25)

**Encargo:** Eugenio pidió «que todas las herramientas funcionen». Es la Tarea 9 de `docs/planes/PLAN_BARRA_SUPERIOR.md`
y el §8.3 del diseño aprobado `docs/especificaciones/2026-10-25-barra-superior-design.md`: en cada una de las 22 pantallas de
`frontend-desktop/src/shell/rutas.ts` se ejecuta la **acción principal** con la cuenta que la puede usar y se comprueba el
**resultado visible**, no solo que la pantalla cargue. Esta bitácora es la **lista de defectos**. No se tocó código de la
aplicación. Ronda 2 (tras el árbitro): `--solo` estricto, comprobación de lo que debe **desaparecer** (`ausentes`), avisos
toast en la regla de errores, y corrida nueva con la barra superior ya montada.

## 1. Cómo se repite

```powershell
# requiere la interfaz compilada (frontend-desktop/dist); el modo funcional sirve una COPIA congelada de ella
uv run --active --with playwright python scripts/recorrido_ux_playwright.py --funcional --salida <carpeta-fuera-del-repo>
# solo algunas filas (con espacios o con comas):  --solo catalogo historico   o   --solo catalogo,historico
# otro archivo de filas:                          --acciones <otro .toml>
```

- **Filas:** `scripts/recorrido_funcional.toml`, una por pantalla (ruta, cuenta, carpeta, proyecto, pasos, lo que debe verse y lo
  que NO debe verse), más dos filas de **siembra** que se corren siempre. El formato está en la cabecera del archivo. Acciones:
  `llenar`, `elegir`, `pulsar`, `marcar`, `subir`, `ir`, `esperar`, `tecla`.
- **`--solo`:** acepta nombres separados por espacios o por comas. **Un nombre que no es una fila del `.toml` es un error**
  (lo dice, lista las filas que hay y sale con 1 sin arrancar nada); `--solo` sin nombres también sale con 1. Cada fila puede
  declarar `requiere = [...]` (filas anteriores de las que depende) y `--solo` las agrega solas y lo avisa: `historico`
  requiere `actualizacion`; `entregar` requiere `hoja`; `revisar` requiere `entregar` (y por ella `hoja`); `historial`
  requiere `libros`.
- **Navegación por URL** (`location.hash = '#/<id>'`), nunca por el menú: vale igual con el menú lateral y con la barra superior
  (la ronda 2 ya corrió sobre la barra). Una página por cuenta, sin recargar (el proyecto elegido vive en la memoria de la
  interfaz, RT-9). La carpeta y el proyecto se eligen con los `select` `#selector-caso` y `#selector-proyecto`; si no se ven, se
  abre el panel con el botón de la barra cuyo nombre empieza por «Carpeta de trabajo». La carpeta se confirma contra la API
  (`GET /v1/casos`), no contra lo que muestra la interfaz (véase D1).
- **Pasa** una fila si (a) se ven todos sus textos esperados, (b) **no se ve ninguno de sus `ausentes`** (por ejemplo, la partida
  sin PVC tras buscar «PVC»), (c) si pide descarga, el archivo bajó y su SHA-256 está en pantalla, y (d) no queda a la vista en
  **toda la página** ningún aviso de error de Carbon: en línea, accionable o **toast** (`.cds--toast-notification--error`).
  `admite_error = true` lo permitiría; ninguna fila lo usa.
- **Salida:** `funcional.json` (por fila: pasos, salida, avisos, errores de consola y de red, carpeta mostrada frente a la de la
  API, segundos; arriba, `solo` y `agregadas_por_requiere`), `capturas/NN_<ruta>.png`, `arbol/NN_<ruta>.txt` (árbol ARIA de las
  filas que fallan), `descargas/`. Sale con 1 si falla una fila o la siembra, si falta una ruta de `rutas.ts` en el `.toml` o si
  `--solo` no es válido.
- **Entorno:** Uvicorn en `127.0.0.1` (puerto libre) con una carpeta de datos TEMPORAL sembrada con la demostración ficticia
  (`start.preparar_demo`: `demo`, `s1`, `ti001`, `of001`, `obra_control`) y las cuentas de `tests/fixtures/sesion_web.py`:
  `admin` (administra), `ana` (arma), `rita` (revisa). Chromium de Playwright sin cabeza; servidor y navegador se cierran por
  su PID. La copia congelada de `dist` evita que otro proceso que recompila la interfaz a mitad del recorrido deje trozos
  perezosos en 404 (pasó en la corrida 2 de la ronda 1: «No se pudo abrir la pantalla… Recargue la página»).
- **Siembra adicional (toda ficticia):**
  1. el administrador guarda la empresa «Contratista Demo, C.A.» (`J-00000000-0`) y genera una **clave de firma de prueba**
     desde el propio equipo;
  2. `ana` revalora DEMO-001 (carpeta `demo`) con **vigencia 2026-10-01** (versión FUN-01): deja cambios de precio
     **anteriores a hoy** para que el filtro de «Histórico» tenga algo que quitar (la demostración no trae ninguno: la tabla
     `cambio_precio` de `demo.db` está vacía). **Límite:** la vigencia tiene que ser posterior a la lista base de DEMO-001
     (2026-09-20); con 2026-06-01 la revaloración se rechaza (409: «el insumo Tuberia PVC 6 pulg no tiene precio en la lista…»),
     porque los insumos que la lista nueva no menciona quedan sin precio en esa fecha. La fecha es fija: el recorrido supone que
     se corre después del 2026-10-01.
  3. el paquete `.silice` lo **genera «Entregar»** en la misma corrida y lo **consume «Revisar un paquete»**.

  Archivos subidos: el libro limpio de `tests/fixtures/libros_empresa.py`, la tasa del BCV `tests/fixtures/bcv/2_1_2c26_smc.xls`,
  `tests/fixtures/precios_empresa_s1.csv` y las muestras ficticias `data/samples/precios/lista_2026-06-01.csv` y
  `data/samples/telecom/topologia_ti001.csv` (las que usan `tests/fixtures/actualizacion_uc02.py` y `tests/fixtures/caso_ti001.py`).
  La cláusula de reajuste es la de `tests/fixtures/reajuste_pantalla.py`. Ningún libro ni dato real.

## 2. Resultado por pantalla (ronda 2, corrida completa sobre la interfaz compilada el 2026-10-25 16:45:32, ya con la barra superior)

**22 de 22 pasan; las dos filas de siembra pasan; ninguna carpeta mostrada distinta de la de la API.** Orden de ejecución = orden
del `.toml`.

| # | Pantalla | Cuenta | Carpeta / proyecto | Acción principal | Resultado visible comprobado | s |
|---|---|---|---|---|---|---|
| 1 | `administracion` | admin | silice (por defecto) | crear la cuenta `func01` con rol arma | «func01» y «Persona Ficticia Uno» en la tabla de cuentas | 4,8 |
| 2 | `indices` | admin | silice | Leer la tasa del BCV y confirmar | «usd_compra: importada (64 valores)», «usd_venta: importada (64 valores)» | 1,5 |
| 3 | `precios_empresa` | admin | s1 | crear la lista de la empresa con el CSV ficticio | «Lista creada» | 2,5 |
| 4 | `acerca` | ana | demo | **solo lectura:** ver versión y bases | «Versión», «Al día» | 0,8 |
| 5 | `inicio` | ana | demo | soltar el libro en «Audite un presupuesto» → «Auditar por mi cuenta» | visor del libro con «Hallazgos (2)» y «Total general» | 1,1 |
| 6 | `catalogo` | ana | demo | buscar «PVC» (antes se ve `LB-01-EXC`) | se ven `LB-02-TUB` y `DEMO-01-INST`; **ya no se ven** `LB-01-EXC`, `LB-03-ENC`, `DEMO-02-VALV` | 0,7 |
| 7 | `componer` | ana | demo | componer `FUN-001` con un material y guardar | «Siguiente paso» y, en el catálogo, `FUN-001` con su descripción | 1,5 |
| 8 | `similares` | ana | demo | buscar «instalacion de tuberia PVC» | «3 propuestas, de mayor a menor similitud» con `DEMO-01-INST` | 39,8 |
| 9 | `simulador` | ana | demo | generar la lista simulada (semilla 42) | «Lista simulada» con sus insumos | 1,0 |
| 10 | `escenarios` | ana | demo | escenario «utilidad alta ficticia» con utilidad 0.20 | «Comparación contra el base» con el escenario | 1,0 |
| 11 | `tablero` | ana | demo / caso de demostración | **solo lectura:** abrir el tablero | «Curva del proyecto», «Partidas que más pesan (Pareto)», «Versiones del presupuesto» | 1,4 |
| 12 | `hoja` | ana | demo / caso de demostración | Parámetros: utilidad 0.12 → «Guardar versión…» con su fuente | «Se guardó la versión FUN-002 con 1 cambio registrado.», «Versión FUN-002 · Sin cambios sin guardar» | 3,1 |
| 13 | `entregar` | ana | demo / caso de demostración | generar el paquete firmado y descargarlo | «Paquete listo y firmado.»; el `.silice` bajó y su SHA-256 es el de la pantalla | 2,4 |
| 14 | `actualizacion` | ana | demo | revalorar DEMO-001 con la lista de muestra (versión FUN-02, vigencia hoy) | «Comparativo por partida», «Informe de auditoría de la versión nueva» | 0,9 |
| 15 | `historico` | ana | demo | filtrar desde hoy (antes se ve `01/10/2026`, de la siembra) | se ven «Cemento Portland» y «Arena lavada»; **ya no se ve** `01/10/2026` | 1,0 |
| 16 | `elaborar` | ana | ti001 | telecom: extraer el cómputo de la topología TI-001 y elaborar | «Presupuesto elaborado», «Informe de auditoría» | 2,9 |
| 17 | `reajuste` | ana | s1 / Contrato S1 (reajuste) | cláusula, componentes, período y ejecutado ficticios → Calcular | «Escalatoria y comprobación, lado a lado» | 3,9 |
| 18 | `control` | ana | obra_control / OBRA-GENERADA | cambiar el umbral de SPI a 0.85 con su fuente | «1 parámetro(s) cambiado(s).» y «0,85» en la tabla | 3,2 |
| 19 | `existencias` | ana | demo | crear el material `ARE-F01` y registrar una entrada de 25 m³ | fila «ARE-F01 Arena lavada ficticia m³ 25 10 Normal» | 3,1 |
| 20 | `revisar` | rita | silice | abrir el `.silice` de la fila 13 y guardar el dictamen | «Total recalculado», «Dictamen guardado, atado al SHA-256 de este archivo.» | 1,7 |
| 21 | `libros` | rita | silice | abrir el libro ficticio | visor con «Hallazgos (2)» y «Total general» | 0,9 |
| 22 | `historial` | rita | silice | ver la auditoría recién guardada | `libro_plantilla_empresa_ficticio.xlsx` en el historial | 0,6 |

Evidencia: `capturas/NN_<ruta>.png` y la fila de `funcional.json` en la carpeta de salida. Ninguna fila tuvo respuestas HTTP
4xx/5xx; las filas 6 y 22 registran errores de consola (D2).

**Corridas de la ronda 2 que prueban `--solo`:** `--solo catalogo historico` → agrega `actualizacion` (requerida), 3 de 3 pasan,
sale 0; `--solo catalogo,historico` → lo mismo, sale 0; `--solo nada` → «ERROR: --solo: no hay fila para nada; las filas son: …»,
sale 1 sin arrancar el servidor; `--solo` vacío → «ERROR: --solo sin rutas…», sale 1.

**Lo que rompió el cambio del front a mitad de la ronda 2** (la barra superior de la Tarea 7 entró en `dist` a las 16:28): el panel
«Carpeta y proyecto» ya no tiene el id `panel-carpeta-proyecto`; el script lo busca ahora por el nombre del botón. En la primera
corrida completa con esa interfaz fallaron dos filas por causas del propio recorrido, no de la aplicación: `hoja` esperaba la
versión «DEMO-002» y, con la siembra nueva (FUN-01), la versión guardada es FUN-002; `similares` no respondió en 120 s con el
equipo cargado (otras sesiones corrían pruebas) y ahora espera hasta 240 s (D5).

## 3. Defectos, de mayor a menor gravedad

Dueño: **armazón** (se corrige en el plan de la barra), **pantalla** (trabajo propio con TDD y árbitro), **`core/`** (bloqueo
para el tutor; no se toca).

| Id | Gravedad | Dueño | Estado (ronda 2) | Defecto | Evidencia | Causa probable |
|---|---|---|---|---|---|---|
| D1 | Alta | armazón | **No se reproduce** con la barra superior (`dist` 16:45:32): en las 22 filas la carpeta mostrada es la de la API, y el `select` del panel ya trae la opción `silice.db`. | El selector «Carpeta de trabajo» mostraba «demo» aunque la sesión trabajaba en `silice.db`: la importación del BCV del admin se guardó en `silice.db`; elegir «demo» no disparaba el cambio. | ronda 1, corrida 5: `resumen.carpeta_mostrada_distinta` = «administracion (admin): muestra 'demo', la sesión usa 'silice.db'» y lo mismo en `indices`. | `frontend-desktop/src/shell/Selectores.tsx:26` (`value={casos.actual.nombre}`) con opciones solo de `casos.casos` (`:30`); la carpeta por defecto no estaba en `listar_casos` (`operacion/base_datos.py:446`). El control `carpeta_mostrada_distinta` queda en cada corrida para que no vuelva. |
| D2 | Media | pantalla (visor del libro) | Sigue. | Errores de página del visor Univer: `[redi]: Cannot find "u4" registered by any injector` (el script guarda los 6 primeros por fila; 24 en una prueba aparte con el visor abierto 10 s) mientras el libro está abierto. El visor sí dibuja la hoja y los hallazgos. | ronda 2, corrida completa: filas 6 (`catalogo`, primera de `ana` tras el visor del Inicio) y 22 (`historial`, tras `libros`): 6 `pageerror` cada una. | `frontend-desktop/src/visor/adaptadorUniver.ts:42-45` (`createUniver` con los `presets`): un complemento del preset de hojas pide un servicio que no se registra. |
| D3 | Media | siembra de la demostración (`start.py`) y texto de `core/` | **Corregido en la demo** por `ca8e6b73` (`start.py` sella el historial): una sonda con Entregar de DEMO-001 como primera acción ya genera el paquete firmado. El texto de `core/` sigue igual. | «Entregar paquete» no funcionaba con la demostración recién sembrada: «Cadena rota en la versión DEMO-001: no tiene eslabón; alguien cambió la base fuera del sistema…». | ronda 1: sonda con aviso «Cadena rota…»; ronda 2: misma sonda, «Paquete listo y firmado.» y huella correcta. | Era `start.py:71-89` sin `sellar_historial`. El texto «alguien cambió la base fuera del sistema» para una versión sin sellar es de `core/budget/cadena.py:374` y `:378-391` (**`core/`: para el tutor**). |
| D4 | Baja | pantalla (`actualizacion`) | Sigue (no se volvió a probar en Bs). | «Actualizar precios» propone USD aunque el presupuesto base esté en Bs; con `s1` y «Drenaje de la clínica / 001» la revaloración falla: «el proyecto esta en Bs y la version FUN-02 en USD: convierta la version (RF-64)…», sin tildes. | ronda 1, corrida 1, `capturas/14_actualizacion.png`. | `frontend-desktop/src/paginas/actualizacion/index.tsx:68` (`MONEDA_POR_DEFECTO`, no la del presupuesto elegido). El texto sin tildes es de `core/budget/persistencia.py:177` (**`core/`: para el tutor**). |
| D5 | Baja | pantalla (`similares`) / aplicación | Sigue. | La primera búsqueda de «Partidas similares» tarda 40-60 s (más de 120 s con el equipo cargado) con solo el esqueleto «Buscando partidas similares», sin decir que está cargando el modelo. | 46,0 s y 58,6 s (ronda 1); 39,8 s, 60,4 s y >120 s (ronda 2). Necesita `paraphrase-multilingual-MiniLM-L12-v2` en la caché local de Hugging Face. | `aplicacion/similares.py:135` (`proponer_similares`) carga `sentence-transformers` dentro de la petición. |
| D6 | Baja | armazón | **No se reproduce** con la barra superior: el aviso sale solo en las filas que cambian de carpeta (3, 16-19). | El aviso «Carpeta de trabajo cambiada» se quedaba en todas las pantallas hasta cerrarlo (15 de 22 capturas en la ronda 1, incluidas filas sin cambio de carpeta). | ronda 1, corrida 5, `avisos` de las filas 7-15. | `frontend-desktop/src/shell/Shell.tsx` (el `aviso` no se limpiaba al navegar). |
| D7 | Baja | pantalla (`historico`) / API | Sin volver a mirar. | Cifras con distinto formato en la misma fila: «Ayudante 4,00 → 3». | ronda 1, sonda Actualizar + Histórico: árbol ARIA, fila «25/10/2026 Ayudante 4,00 3 -25». | El precio anterior llega como lo guardó la lista base («4.00») y el nuevo como el CSV («3»); la pantalla los muestra tal cual. |

**Observaciones que no son defectos:** (1) en «Revisar un paquete», el paquete firmado por la misma instalación sale
«No verificado: … su clave no está registrada en esta instalación»; es lo previsto (hay que registrarla en «Empresas
registradas») y el recorrido no la registra. (2) El visor del libro tarda unos segundos en dibujar la cuadrícula; la captura
tomada al ver los hallazgos la muestra gris y 10 s después la hoja está dibujada. (3) Inicio dice «Caso abierto: silice.db»
con la extensión, mientras la barra la oculta («silice»).

**Defectos del propio script (corregidos):** `rutas_de_la_interfaz()` devolvía 0 páginas cuando `rutas.ts` ganó el campo
`enUnaLinea` (ahora lee cada campo por su nombre); en la ronda 1, `--solo` con un nombre desconocido o con comas filtraba a 0
filas y salía con 0 (falso verde; ahora sale con 1); y `catalogo` e `historico` pasaban aunque el filtro no filtrara (ahora
exigen `ausentes`, y antes de filtrar comprueban que lo que debe desaparecer sí se veía).

## 4. Lo que el recorrido no cubre todavía

Cada fila prueba **la acción principal**; no prueba todo lo que la pantalla hace. `acerca` y `tablero` son de **solo lectura**:
su fila prueba que muestran datos del caso, no una escritura. Quedan sin ejecutar: en Administración, las pestañas Empresas
registradas, Claves de API, Asistente de IA, Accesos e Instalación; en Existencias, «Importar báscula» y «Pesajes sospechosos»;
en la Hoja, las pestañas distintas de Parámetros (espacio, planos DXF/IFC, Excel, conversión de moneda); en Control de obra,
valuaciones, valor ganado y recuperación; en Reajuste, «Guardar el estudio» y su Excel; el recorrido guiado del Inicio; la
verificación «Verificado» de un paquete (exige registrar la clave pública en «Empresas registradas»). Ninguna pantalla quedó sin
ejecutar por falta de datos.
