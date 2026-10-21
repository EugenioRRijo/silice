# Plan del retiro de Streamlit y del re-congelado del experimento

**Autor:** subagente autor del plan · **Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-retiro-streamlit`
(creada desde `origin/inc/ruta-s2-mig-adm-empresa`, `f2cd316d`) · **Estado:** plan, sin ejecutar ni arbitrar.

**Decisión de Eugenio (2026-10-21):** retiro definitivo de Streamlit y descongelado del experimento por la
**opción A** de `docs/bitacora/2026-10-19-congelado-del-experimento-roto-por-la-migracion.md`: re-congelar a propósito
contra las rutas definitivas («este será nuestro definitivo»). El front definitivo es React (`frontend-desktop`) sobre
`api/` y `aplicacion/`.

Todo lo de abajo se **midió** en esta rama el 2026-10-21 (AST, `rg`, `pytest --collect-only`). Lo que no se pudo medir
dice «no medido». Los scripts de medición eran efímeros (scratchpad); el de equivalencia está en el Apéndice A.

---

## 0. Resumen ejecutivo

| Dato medido | Valor |
|---|---|
| Archivos `.py` en `ui/` | 51 (28 en `ui/`, 23 en `ui/paginas/`), **15 471 líneas** |
| Importan `streamlit` | 29 (7 de `ui/` + 22 páginas); importan `altair`: 1 (`ui/graficos.py`) |
| Líneas por clase | Streamlit puro 10 415 (páginas 8 894 + 7 módulos 1 521); lógica sin Streamlit solo de pantalla 1 539; `ui/hoja.py` 2 835; puentes y resto 642 + 40 |
| Archivos fuera de `ui/` y `tests/` que importan `ui` | **12**: 7 en `asistente/` y 5 en `scripts/` (ninguno en `aplicacion/`, `api/`, `core/`, `adapters/`, `operacion/`, `ml/`, `fusion/`) |
| Suite (esta rama) | 454 archivos con pruebas, **9 351 ítems** recogidos |
| Pruebas que importan `ui` | 111 archivos `.py` (104 con pruebas, **2 436 ítems**; 7 son `conftest.py` o fixtures) |
| Pruebas AppTest | 45 archivos (44 con pruebas, **658 ítems**) |
| Paridad contra `ui.hoja` vivo | 7 archivos `test_aplicacion_hoja_paridad*` (**201 ítems**) más usos de `clasica` en otros 9 archivos |
| Guardia del congelado | **ya está roja** en esta rama (comprobado: `1 failed`); sigue roja hasta la fase F11 |

Hallazgos que cambian el alcance (no estaban en el encargo):

1. **El producto instalado arranca Streamlit, no React.** `operacion/lanzador.py:308` lanza `streamlit run ui/app.py` como
   proceso principal, el puerto por defecto es `PUERTO_STREAMLIT = 8501` (`operacion/config.py:79`), la sonda de salud
   apunta a ese puerto y la API (que sirve `/app`) está **apagada por defecto** (`Ajustes.api_activa = False`). Retirar
   `ui/` sin rehacer el lanzador deja el producto sin interfaz. Es la fase F2 y necesita decisión de Eugenio.
2. **`python-multipart` solo llega por Streamlit.** En `uv.lock` la única dependencia que lo trae es `streamlit`
   (junto con `httptools`, `websockets`, `watchdog`, `pyarrow`). La API usa `File`/`Form`/`UploadFile`
   (`api/archivos.py`, `api/rutas/libros.py`, `api/rutas/computos.py`, …): quitar el extra `ui` sin añadir `python-multipart`
   al extra `api` rompe las subidas al importar las rutas.
3. **El panel del asistente de IA de la Hoja no existe en React** (`frontend-desktop/src/paginas/hoja/index.tsx:505-506`:
   `<aside aria-label="Asistente de IA" hidden />`; ninguna ruta de `api/` usa `asistente.servicio`). Retirar Streamlit
   deja `asistente/servicio.py` sin interfaz. Pregunta abierta Q2.
4. **Hay dos clases `Borrador`** (`ui.hoja.Borrador`, usada por `asistente/`, y `aplicacion.hoja.Borrador`, usada por la API).
   Los cuerpos son iguales, pero un `Borrador` de una no es de la otra: la conmutación de `asistente/`, los fixtures y las
   pruebas debe ser **atómica** (fase F7).

---

## 1. Inventario de `ui/` (medido)

Clases: **(a)** Streamlit puro, se borra · **(b)** lógica sin Streamlit que alguien de fuera importa, hay que mover o
reapuntar · **(c)** puente de reexportación a `aplicacion/`, se borra tras mover sus pruebas · **(d)** lógica sin Streamlit
que solo sirve a las pantallas, se borra con ellas.
«Ext.» = importadores fuera de `ui/` y `tests/`. «Pruebas» = archivos de `tests/` que lo importan.

### 1.1 Módulos de `ui/`

| Archivo | Líneas | Streamlit/altair | Ext. | Pruebas | Clase y destino |
|---|---:|---|---|---:|---|
| `acceso.py` | 225 | st | — | 1 | (a) borrar |
| `app.py` | 331 | st | — | 8 | (a) borrar (enrutador; lo lanzan `operacion/lanzador.py` y `start.py`) |
| `barra.py` | 318 | st | — | 3 | (a) borrar |
| `caso.py` | 248 | st | — | 13 | (a) borrar (la API tiene `api/caso_web.py`) |
| `cliente.py` | 65 | st | — | 4 | (a) borrar (`aplicacion/equipo.py` ya tiene la lógica) |
| `resultado.py` | 172 | st, pandas | — | 2 | (a) borrar |
| `sesion.py` | 162 | st | — | 13 | (a) borrar (la API tiene `api/sesion_web.py`) |
| `graficos.py` | 117 | altair | — | 1 | (d) borrar (la gráfica de React es propia) |
| `libros.py` | 797 | — | — | 2 | (d) borrar (la API usa `adapters.hoja_empresa.visual`) |
| `existencias.py` | 367 | — | — | 1 | (d) borrar (la API usa `produccion.*` directo) |
| `recorridos.py` | 249 | — | — | 6 | (d) borrar (React tiene `shell/recorrido.ts`) |
| `texto_seguro.py` | 9 | — | — | 5 | (d) borrar (escapa Markdown de Streamlit) |
| `entorno.py` | 40 | — | — | 3 | (b) mover `VARIABLE_CASO`, `ALIAS_ANTERIORES`, `leer_variable` a `aplicacion/entorno.py` (los importa `tests/conftest.py:17`); luego borrar |
| **`hoja.py`** | **2 835** | — | **10** | 54 | **(b)** copia de `aplicacion/hoja.py`; ver §1.4 |
| `composicion.py` | 53 | — | 1 (`scripts/simular_corpus.py`) | 8 | (c) reexporta `aplicacion.composicion`; ver §1.4 |
| `control.py` | 124 | — | 1 (`scripts/medir_rnf15.py:48`) | 2 | (c) reexporta `aplicacion.control` |
| `atipicos.py` | 40 | — | — | 3 | (c) conserva solo `avisos` con escape Markdown (Streamlit); borrar |
| `elaboracion.py` | 57 | — | — | 5 | (c) |
| `entrega.py` | 37 | — | — | 6 | (c) |
| `estilo.py` | 34 | — | — | 1 | (c) |
| `indices.py` | 15 | — | — | 2 | (c) |
| `precios_empresa.py` | 24 | — | — | 2 | (c) |
| `proyectos.py` | 32 | — | — | 3 | (c) |
| `reajuste.py` | 45 | — | — | 3 | (c) |
| `revision.py` | 126 | — | — | 4 | (c) |
| `subidas.py` | 12 | — | — | 2 | (c) |
| `tablero.py` | 42 | — | — | 0 | (c) sin pruebas propias |
| `__init__.py` | 1 | — | (`from ui import …`) | — | se borra al final |

(«Pruebas» cuenta archivos de `tests/` que importan ese módulo; `ui/hoja.py` tiene 54. El número de «Ext.» de `hoja.py` son
los 7 archivos de `asistente/` que lo importan más `seed_of001`, `medir_rnf11` y `prueba_real_asistente`.)

### 1.2 Páginas (`ui/paginas/`, todas clase (a), se borran)

22 páginas + `__init__.py`, 8 894 líneas, todas importan `streamlit`: `acerca` 40, `actualizacion` 415, `administracion` 802,
`catalogo` 99, `componer` 870, `control` 545, `elaborar` 487, `entregar` 170, `escenarios` 226, `existencias` 526,
`historico` 91, **`hoja` 2 308**, `indices` 157, `inicio` 162, `instalacion` 110, `libros` 631, `precios_empresa` 152,
`reajuste` 247, `revisar` 336, `similares` 179, `simulador` 138, `tablero` 196.
Cada una tiene carpeta homóloga en `frontend-desktop/src/paginas/` (`instalacion` vive dentro de `administracion`, ruta
`api/rutas/admin_instalacion.py`). **Paridad funcional pantalla por pantalla: no verificada por este plan**; es el
criterio de aceptación del Plan de la migración final y de la prueba de navegador de Eugenio, no de esta tarea.

### 1.3 Importadores externos (los 12 archivos)

| Archivo (fuera de `ui/`, `tests/`) | Qué importa | En `archivos_del_auditor` |
|---|---|---|
| `asistente/validacion.py:34` | `from ui.hoja import Borrador, HojaInvalida` | sí |
| `asistente/orquestador.py:59` | ídem | sí |
| `asistente/privacidad.py:24` | `from ui.hoja import Borrador` | sí |
| `asistente/propuestas.py:20` | `from ui.hoja import (…)`; el comentario de `:45` cita `ui.hoja.COLUMNAS` | sí |
| `asistente/experimento/banco.py:30` | `from ui.hoja import Borrador, espacio_desde_filas` | sí |
| `asistente/experimento/ejecucion.py:43-44` | `from ui import hoja`; `from ui.hoja import Borrador` | sí |
| `asistente/servicio.py:29-30` | `from ui import hoja`; `from ui.hoja import Borrador, HojaInvalida` | **no** |
| `asistente/catalogo.py:4` | solo docstring («`ui.hoja`») | sí (no se toca: ver §3) |
| `scripts/seed_of001.py` | `ui.hoja` | no |
| `scripts/medir_rnf11.py` | `ui.hoja` | no |
| `scripts/prueba_real_asistente.py` | `ui.hoja` | no |
| `scripts/medir_rnf15.py:48` | `ui.control` | no |
| `scripts/simular_corpus.py` | `ui.composicion` (`FilaReferencia`, `buscar_referencia`, `composicion_desde_tablas`, 3 `fila_*_desde_referencia`) | no |

(`asistente/catalogo.py` solo cita `ui.hoja` en un docstring: no es importador, por eso los importadores son 7 + 5 = 12.)
Importes dinámicos: `ui/barra.py:113,118` usa `importlib.import_module("ui.hoja")`; los demás `importlib` del repo no apuntan a `ui`.

### 1.4 Verificación de la afirmación «`aplicacion/hoja.py` es AST-idéntica a `ui/hoja.py`»

Medido con `ast.dump` por definición (sin docstrings), HEAD de esta rama:

- `ui/hoja.py` (2 835 líneas) y `aplicacion/hoja.py` (2 842): **mismo conjunto de 121 definiciones de primer nivel, todas
  idénticas** (`distintos: []`). Difieren solo en el docstring y en **3 importaciones**: `ui.composicion` →
  `aplicacion.composicion`, `ui.estilo` → `aplicacion.estilo`, `ui.subidas` → `aplicacion.subidas`.
  La afirmación es cierta con esa salvedad. `Borrador` es **otra clase** en cada módulo (`ui/hoja.py:327`,
  `aplicacion/hoja.py:334`).
- Contra el **congelado** (`git show cd46732:ui/hoja.py`, 2 838 líneas): la única definición que falta hoy es
  `HojaInvalida`, que se movió a `aplicacion/errores.py` (commit `bdf77cc`; las dos hojas la importan de allí). El resto de
  definiciones y asignaciones son idénticas. No cambia ninguna regla de negocio.
- `ui/composicion.py` congelado (734 líneas) vs `aplicacion/composicion.py` HEAD: **todas las definiciones del congelado
  están idénticas** en `aplicacion/`; esta tiene **además** 20 definiciones nuevas (`Advertencia`, `Evaluacion`,
  `Guardado`, `Precarga`, `evaluar_composicion`, `guardar_composicion`, `precarga_de_partida`, `presentar`,
  `similares_con_composicion`, …) y varias constantes `MENSAJE_*`, añadidas por la migración de Componer. Re-congelar contra
  `aplicacion/composicion.py` **amplía** lo que el auditor hashea (decisión Q4).
- `ui/composicion.py` HEAD (53 líneas) es una reexportación explícita de `aplicacion.composicion`. Igual el resto de los
  puentes de la clase (c): importan de `aplicacion.*` y no definen lógica (0 `def`/`class`) salvo `ui/atipicos.py` (1 función
  `avisos`) y `ui/entorno.py` (1 función `leer_variable`, sin equivalente en `aplicacion/`).
- Otras copias: `aplicacion/hoja_*.py` (`vista`, `edicion`, `guardado`, `versiones`, `borradores`, `exportar`, `plano`) son
  código **nuevo** de la migración, no copias; `aplicacion/entorno.py` **duplica a propósito** `ui.app.modo_entrega_activo`
  y añade `url_clasica` (ver F2/F10).

### 1.5 Lo no-Python que menciona Streamlit (medido con `rg -i streamlit|altair`)

Funcional (rompe si se quita Streamlit):

| Archivo | Qué hace |
|---|---|
| `pyproject.toml:29` | extra `ui = ["streamlit>=1.62", "altair>=6"]`; `[tool.ruff.lint.isort] known-first-party` incluye `"ui"` |
| `uv.lock` | `streamlit` (l.3246), `altair`; cierre exclusivo de la UI (calculado con `tomllib`): `altair, attrs, httptools, jsonschema, jsonschema-specifications, protobuf, pyarrow, pydeck, python-multipart, referencing, rpds-py, streamlit, toml, watchdog, websockets` = 15 paquetes |
| `.streamlit/config.toml` | tema y opciones; `instalador/streamlit_config.toml` es su copia oficial del instalador |
| `operacion/lanzador.py` (`orden_streamlit`, `opciones_streamlit`, `("streamlit", …)` en `:308`), `operacion/config.py:79,122,184` (`PUERTO_STREAMLIT`), `operacion/red.py`, `operacion/registro.py`, `operacion/__init__.py`, `operacion/ordenes_100.py` | arranque y red del producto |
| `start.py:12,35,124-126` | arranque de demostración con `streamlit run ui/app.py` en el 8501 |
| `instalador/manifiesto.py:21,200-209`, `instalador/manifiesto.toml:11,20,22` (capa `ui` y paquete `ui`), `instalador/medir_capas.py:35-43`, `instalador/humo.ps1:33,224-242,297-299` (8501 y `.streamlit\config.toml`), `instalador/navegador.py` | construcción y humo del instalador |
| `.github/workflows/instalador.yml:126` | `uv sync --locked --extra ui …`; `ci.yml` usa `--all-extras` (no cambia) |
| `scripts/prueba_data_editor.py` (importa `streamlit`), `scripts/medir_data_editor.md`, `scripts/meta_silice.py:146-147` (pares TDD `ui/entorno.py`, `.streamlit/config.toml`), `scripts/meta_silice_s2.py:95`, `scripts/meta_silice_s3.py:44,61-87` (10 pares con ruta `ui/…` y `CARPETAS_SIN_HTML_INSEGURO = ("ui", …)`), `scripts/meta_silice_s5b.py:70-73`, `scripts/meta_prototipo.py:47,210-213` (P7 exige `ui/composicion.py`) | metas y utilidades (17 filas `ParTDD` con ruta `ui/` o `.streamlit/` en total) |
| `api/rutas/sesion.py:53,116,139` + `aplicacion/entorno.py` (`url_clasica`), `docs/api.json` (4 menciones: l.750, 851, 10439, 17171), `api/*.py` y `aplicacion/*.py` (docstrings) | el campo `url_clasica` es contrato de la API: quitarlo cambia `docs/api.json` |
| `frontend-desktop/src/App.tsx:13-15,52`, `api/tipos.ts:17-18`, `shell/MenuLateral.tsx:14-27,54`, `shell/rutas.ts` y sus pruebas | `VITE_URL_CLASICA`, `PaginaSinMigrar`, `urlClasica` |

Documentación viva (se actualiza): `README.md` (3 menciones), `NORMAS.md` (5; además el árbol de §6 y la línea
`.streamlit/config.toml`), `docs/ERS.md` (12; incluye **RT-4** «Streamlit sigue siendo la principal», RF-36/37/42/81,
RNF-11/15), `docs/arquitectura.md` (21), `docs/manual_tecnico.md` (11), `docs/manual_usuario.md` (4), `docs/plan_pruebas.md` (6),
`docs/guion_prueba_arenia.md` (9), `docs/metodologia.md` (1), `docs/protocolo_indicador3.md` (2), `docs/protocolo_asistente.md:110`
(cita `ui/hoja.py` como archivo del auditor), `scripts/README.md` (2), `frontend-desktop/{README,DESIGN,PRODUCT}.md` (5).

Historia que **no se reescribe** (describe cómo se hizo): `CHANGELOG.md` (solo se añade), `PLAN_*.md` de la raíz,
`docs/bitacora/**`, `docs/auditoria/**`, `docs/especificaciones/**`, `docs/planes/**` anteriores a este, `docs/tesis/**`
(22 archivos entre tesis y bitácora citan Streamlit). Si una guardia (p. ej. `test_nombre_silice`, `meta_datos`) recorre alguno
de ellos, se ajusta la guardia, no el texto.
No medido: `graphify-out/`, el vault de Obsidian y `.claude/`/`.agents/` (el agente `sf-ingeniero-interfaz` nombra `ui/`).

---

## 2. Pruebas (medido)

Base: `pytest --collect-only -q` en esta rama = **9 351 ítems en 454 archivos** (el tiempo de la suite completa: no medido).

| Disposición | Archivos | Ítems | Qué es |
|---|---:|---:|---|
| **BORRAR** — AppTest de páginas y del marco | 44 (+ `tests/fixtures/paginas_s3.py`, sin ítems) | **658** | los `test_ui_*` con `AppTest`, `test_apptest_timeout_comun`, `test_config_streamlit`; ver §2.1 |
| **BORRAR** — módulos retirados sin Streamlit | 5 | 46 | `test_ui_caso` 16, `test_ui_recorridos` 22, `test_libro_visual` 6, `test_texto_seguro` 1, `test_ui_importable` 1 |
| **REESCRIBIR** — paridad contra `ui` vivo | 7 | **201** | `test_aplicacion_hoja_paridad{,_apu,_espacio,_guardado,_planos,_secciones,_versiones}.py` |
| **REESCRIBIR** — oráculo `clasica` suelto | 9 | (dentro de los 1 578) | `test_api_hoja{,_conversion_cadena,_edicion,_exportar,_guardado,_plano,_versiones}.py`, `test_aplicacion_hoja_{plano,vista}.py` |
| **MIGRAR** — solo cambia el import | 57 | 1 578 | la lógica pasa a `aplicacion.*`; 62 archivos importan `ui.hoja`/`ui.composicion` (1 571 ítems, solapados con las filas anteriores) |
| **ADAPTAR** — guardias y textos | ≈ 15 de 38 | (de 1 253 + 6) | `test_arquitectura{,_asistente,_s1,_s2,_s3,_s5}`, `test_lanzador` (28 funciones, 65 ítems), `test_manifiesto`, `test_medir_capas`, `test_extras_perezosos`, `test_ui_sin_cdn` (se borra), `test_dependencias_silice`, `test_meta_silice*`, `test_entorno_silice`, `test_aplicacion_entorno`, `test_nombre_silice` (importa `ui.app`; guarda el nombre «Sílice» en documentos vigentes, se conserva); el resto solo cita `ui/` en un docstring |

(Las filas pueden solaparse en archivos mixtos; el reparto es por la disposición dominante del archivo. El número exacto de
funciones por disposición dentro de los archivos mixtos se fija en el triaje de F3, no se estima aquí.)

### 2.1 AppTest: qué se borra y qué se rescata

En los 46 archivos de `tests/unit` con `AppTest`/`streamlit` (incluye `test_meta_sf.py`, que solo lo cita en un comentario y
**no** se borra), quedan 524 funciones `test_*` sin contar `test_meta_sf`: **403 usan Streamlit** (cierre transitivo de
ayudantes dentro del archivo; se borran) y **121 no** (prueban lógica pura de `aplicacion/` a través de un puente `ui.*` o
funciones de `ui/caso`, `ui/existencias`, `ui/libros`). Estas 121 se **triagan una por una en F3** antes de borrar: si
ejercitan `aplicacion/` y no tienen homólogo (`test_aplicacion_*`, `test_api_*`), se mueven; si prueban un módulo que se
retira, se borran con él. Las que más tienen sin AppTest: `test_ui_tablero` (21), `test_ui_libros` (22), `test_ui_app` (12),
`test_ui_cliente` (10), `test_ui_existencias` (9), `test_ui_marco` (8), `test_ui_roles` (7).

### 2.2 Oráculos que hay que conservar como literales a mano

Ya son literales casi en todas partes (`D("2703.86")`…). Lo que exige cuidado es **no perderlos al borrar** las pruebas de
paridad y de página. Dónde viven hoy (archivo:línea):

| Valor | Literal ya escrito a mano en |
|---|---|
| Total OF-001 **2 703,86** | `tests/integration/test_aceptacion_sf.py:60`; `tests/unit/test_api_hoja_guardado.py:99`; `test_api_hoja_conversion_cadena.py:68`; `test_api_hoja_plano.py:96`; `test_api_hoja_versiones.py:94`; `test_api_hoja_edicion_secciones.py:247,289,503,504,674`; `test_api_hoja_apu_retomar.py:255,313`; `test_api_hoja_exportar.py:271`; `tests/integration/test_guion_cp10_cp11.py:39,143`; `tests/integration/test_hoja_versiones.py:116`; en paridad: `test_aplicacion_hoja_paridad.py:228,270`, `…_secciones.py:208,321,396`, `…_guardado.py:57` |
| v002, administración 0,20 → **2 821,42** (exacto 2 821,4208) | `test_api_hoja_guardado.py:96,356`; `test_api_hoja_versiones.py:362,1148`; `test_api_hoja_edicion_secciones.py:400`; `test_api_hoja_exportar.py:294`; en paridad: `test_aplicacion_hoja_paridad.py:289`, `…_secciones.py:244`, `…_guardado.py:56` |
| PE **1 763,39** | `test_api_hoja_edicion_secciones.py:402`; `test_api_hoja_guardado.py:10` (docstring); `test_api_hoja_versiones.py:1138` (docstring); en paridad: `…_paridad.py:290`, `…_secciones.py:245` |
| **62,50 %** | `test_api_hoja_guardado.py:98,376`; `test_api_hoja_versiones.py:1127,1147,1168`; `test_api_hoja_edicion_secciones.py:403`; en paridad: `…_paridad.py:291`, `…_secciones.py:246` |
| PE 1 530,49 (Día 23), 56,60 %, CV 2 137,44 | citados en `test_aplicacion_hoja_paridad.py:11-12`; **no medido** dónde se aserta cada uno fuera de la paridad (grep puntual en F6 antes de borrar) |
| Línea base clínica (PU 8,60 · 10,19 · 33,24 · 242,64 · 52,58; 1 586,61) | `tests/fixtures/apu_linea_base.py` (única copia; no depende de `ui`) |

Regla de F6: antes de borrar una aserción de paridad, el implementador demuestra con `rg` que el mismo literal sigue asertado
por una prueba que **no** importa `ui` (tabla de arriba); si no, la reescribe como literal.

---

## 3. Descongelado y re-congelado (medido)

- **Qué cambia en `asistente/experimento/protocolo.json`** (`archivos_del_auditor`, 49 rutas): `ui/hoja.py` →
  `aplicacion/hoja.py` (línea 59) y `ui/composicion.py` → `aplicacion/composicion.py` (línea 60). Opcional (Q4):
  añadir `aplicacion/errores.py` (donde vive `HojaInvalida`, que el auditor importa y que estaba dentro de `ui/hoja.py` al
  congelar). Cambia por consiguiente la huella `protocolo` (el archivo se hashea entero).
- **Archivos del auditor que cambian de import** (solo líneas `import` y un comentario): `asistente/validacion.py`,
  `orquestador.py`, `privacidad.py`, `propuestas.py`, `experimento/banco.py`, `experimento/ejecucion.py`. Mismo cambio, fuera
  de la lista: `asistente/servicio.py`. **No se tocan** `asistente/catalogo.py` (solo docstring), `tests/fixtures/caso_of001.py`
  ni `caso_ti001.py`/`asistente_banco.py`: están en la lista y cualquier byte cambiado altera la huella; si en F7 hace falta
  tocar un docstring de ellos, se declara en el commit y la prueba de equivalencia lo cubre.
- **Comando para regenerar `congelado.json`** (`asistente/experimento/congelado.py:65`; `congelar` exige árbol **limpio** y
  escribe `banco`, `protocolo`, `auditor`, `commit`):

  ```powershell
  # árbol limpio, todo lo anterior ya committeado
  $env:VIRTUAL_ENV='C:\Users\euger\OneDrive\Escritorio\TESIS\.venv'
  uv run --active --no-sync python -c "from asistente.experimento.congelado import congelar; import subprocess; print(congelar(subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()))"
  git commit asistente/experimento/congelado.json   # asunto: chore(asistente): re-congelar el experimento contra las rutas definitivas
  ```
  (El congelado original, `9181862d`, se hizo igual — receta en `PLAN_SILICE_090.md:13890` —; guardó el commit abreviado
  `cd46732`; ahora guardará el SHA completo. Como `congelado.json` ya está versionado, basta `git commit <ruta>`.)
- **Orden para dejar `test_experimento_congelado_vigente` verde solo al final:** la prueba está roja hoy y lo estará durante
  F1–F10 (se acepta y se declara: «la única roja conocida»). F11 hace, en este orden: (1) commit `protocolo.json` con las rutas
  nuevas; (2) comprobar que `calcular()["banco"]` es igual al de `congelado.json` (el banco no se toca); (3) commit aparte de
  `congelado.json`. Nada más puede cambiar entre F11(1) y F11(3).
- **Prueba de equivalencia (la lógica del auditor no cambia).** Se corre en F7, antes del commit de conmutación, y su salida se
  copia a la bitácora. Criterio exacto (Apéndice A):
  1. Para cada archivo de `asistente/` que cambia: `ast` del contenido en `cd46732` vs el de HEAD, **tras normalizar** los
     nodos `Import`/`ImportFrom` (`ui`→`aplicacion`, `ui.hoja`→`aplicacion.hoja`) y quitar docstrings: deben ser iguales.
  2. `aplicacion/hoja.py` HEAD vs `ui/hoja.py` en `cd46732`: mismas definiciones y asignaciones idénticas; la única definición
     ausente es `HojaInvalida` (en `aplicacion/errores.py`, que se compara aparte con su definición en `cd46732`).
  3. `aplicacion/composicion.py` HEAD ⊇ `ui/composicion.py` en `cd46732`: toda definición del congelado está idéntica; las
     demás son adiciones listadas.
  4. Conductual: la suite del auditor (`tests/unit/test_asistente_*.py`, `test_experimento_*.py`, `test_hoja_origen_ia.py`,
     `tests/integration/test_clave_ia_nunca_aparece.py`) en verde con `-W error`, y el banco (`calcular()["banco"]`) igual
     al de `congelado.json`.
  5. `git diff cd46732 HEAD -- core/verification adapters/espacio core/contracts core/budget/presupuesto.py` vacío (la
     bitácora de 2026-10-19 ya lo mostró vacío para `core/verification` y `adapters/espacio/reglas.py`; el resto de la lista:
     no medido).

---

## 4. Fases (commits pequeños; suite verde en cada una salvo la guardia del congelado)

Convenciones de todas las fases: commit por tarea, `git commit <ruta…>` (nunca `add -A`, `--amend`, `reset`, `checkout`,
`stash`, `clean`), asunto en español **sin tildes**, línea final `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
TDD con **rojo visto** donde se escribe código o una guardia; las fases de borrado se prueban con la guardia de importación
(F1) y con la suite. Revertir = `git revert <sha>` del commit (o de la tanda), nunca `reset`. Un árbitro (Manual del árbitro)
aprueba cada fase antes de integrarla. Sin push ni PR hasta F11.

### F0 · Línea base (sin commit de código)
Objetivo: fijar los números de partida. Hacer: correr los comandos de §6 sobre la rama intacta y anotar: pruebas verdes, ruff,
`app.openapi()==docs/api.json`, `scripts/meta_silice.py --version 0.6.0 --hasta S1-5` y `--version 0.7.0 --hasta S2-2` (la CI
los corre), y confirmar que la única roja es `test_experimento_congelado_vigente`. Salida: tabla pegada en la bitácora de F1.
Riesgo: ninguno. Revertir: n/a.

### F1 · Guardia de importación y scripts a `aplicacion`
- **Objetivo:** nada fuera de `ui/` y `tests/` importa `ui` salvo `asistente/` (hasta F7); los 5 scripts apuntan a `aplicacion`.
- **Archivos:** `tests/unit/test_arquitectura_retiro.py` (nueva); `scripts/seed_of001.py`, `medir_rnf11.py`,
  `medir_rnf15.py`, `prueba_real_asistente.py`, `simular_corpus.py`; sus pruebas (`test_seed_of001`, `test_medir_rnf11`,
  `test_medir_rnf15`, `test_prueba_real_asistente{,_r17}`, `test_simular_corpus`) solo si importan `ui`.
- **Pruebas (TDD):** (1) escribir la guardia «ningún `.py` fuera de `ui/`, `tests/` y la lista `PENDIENTES = {asistente/…}`
  importa `ui`» → **rojo visto** (5 scripts); (2) cambiar imports (`from aplicacion import hoja`, `aplicacion.control`,
  `aplicacion.composicion`) → verde. `PENDIENTES` baja a vacío en F7.
- **Salida:** guardia verde; las pruebas de esos scripts verdes. Medidas RNF-11/15: la cifra se registra, no se compara
  (la CI «solo registra»).
- **Riesgo:** bajo (mismas funciones, ya idénticas). **Revertir:** `git revert`.

### F2 · El producto arranca sin Streamlit (decisión Q1; carril propio)
- **Objetivo:** `operacion/lanzador.py` lanza solo Uvicorn (`api.main:app`) y abre `http://…/app/`; el instalador, el humo y
  `start.py` ya no mencionan Streamlit.
- **Archivos:** `operacion/{lanzador,config,red,registro,__init__,ordenes_100}.py`, `start.py`,
  `instalador/{manifiesto.py,manifiesto.toml,medir_capas.py,humo.ps1,navegador.py}`, **borrar** `instalador/streamlit_config.toml`,
  `.github/workflows/instalador.yml` (quita `--extra ui`), pruebas `test_lanzador`, `test_ajustes`, `test_manifiesto`,
  `test_medir_capas`, `test_arquitectura_s5`, `test_construir`, `test_programa`.
- **Diseño a ratificar:** puerto único (hoy `[servidor] puerto = 8501` y `[api] puerto = 8000`; propuesta: la clave `[servidor] puerto`
  pasa a ser el de Uvicorn y `[api] activa` se ignora con aviso), `SILICE_DIRECCION`, sonda de salud sobre `/salud` o `/app/`,
  mensajes de `operacion/lanzador.py:335`, lectura compatible de `silice.toml` ya escritos.
- **Pruebas (TDD):** reescribir primero `tests/unit/test_lanzador.py` (28 funciones, 65 ítems; hoy asertan `orden_streamlit(...)`
  con `"ui/app.py"`) para exigir una sola orden (`orden_uvicorn`) y la sonda → rojo visto; luego implementar. `humo.ps1` se
  prueba en el instalador de la CI (no local).
- **Salida:** `test_lanzador`, `test_ajustes`, `test_manifiesto`, `test_construir`, `test_programa` verdes; en `instalador.yml`,
  el job `construir` sin `--extra ui`; humo contra `127.0.0.1:<puerto>/app/`. **El humo del instalador real: no medido**
  (requiere la CI de Windows).
- **Riesgo:** **alto** (es el único camino por el que el usuario final ve algo; cambia la semántica de `silice.toml`). Mitigación:
  fase aparte, árbitro propio, y prueba manual de Eugenio con `start.py --sin-demo`. **Revertir:** `git revert` de la tanda;
  mientras F2 no aterrice, **F4 en adelante no se integra** (el producto aún lanza `ui/app.py`).
- **Paralelo:** sí con F1 y F3 (carpetas disjuntas: `operacion/`, `instalador/`, `start.py`, `.github/workflows/instalador.yml`).

### F3 · Rescatar lo que sirve de las pruebas de `ui` (triaje de las 121)
- **Objetivo:** que borrar los AppTest no pierda cobertura de lógica de `aplicacion/`.
- **Hacer:** por cada archivo de §2.1 con funciones sin AppTest, clasificar cada `test_*` (mover / borrar con el módulo
  retirado) y moverlo a `tests/unit/test_aplicacion_<modulo>.py` cambiando `from ui…` → `from aplicacion…`; los que prueban
  `ui/caso`, `ui/existencias`, `ui/libros`, `ui/recorridos`, `ui/texto_seguro` se anotan como «retirados con su módulo» en la
  tabla del commit. Pegar la tabla (archivo → destino por función) en la bitácora de la fase.
- **Pruebas:** el mismo `pytest` de los destinos; el «rojo visto» no aplica (son pruebas ya verdes que cambian de casa): se
  sustituye por «ítems movidos + ítems borrados = ítems de origen» en la tabla.
- **Salida:** tabla completa sin filas «sin decidir»; suite verde.
- **Riesgo:** medio (perder una aserción). Mitigación: el árbitro compara la tabla con `git diff --stat`. **Revertir:** `git revert`.
- **Paralelo:** por archivo, sí (cada implementador un conjunto disjunto de `tests/unit/test_ui_*.py`), con una sola persona dueña de
  los `tests/unit/test_aplicacion_*.py` destino (ver §5).

### F4 · Borrar la capa Streamlit
- **Objetivo:** fuera `ui/paginas/**`, `ui/{app,barra,acceso,caso,cliente,resultado,sesion,graficos,libros,existencias,recorridos,texto_seguro}.py`
  y sus pruebas.
- **Archivos:** lo anterior; los 44 archivos AppTest (658 ítems) de §2; `tests/fixtures/paginas_s3.py`;
  `tests/unit/{test_config_streamlit,test_apptest_timeout_comun,test_ui_importable,test_ui_sin_cdn,test_ui_caso,test_ui_recorridos,
  test_libro_visual,test_texto_seguro}.py`; en `tests/conftest.py` el piso `PISO_TIMEOUT_APPTEST` (import de `AppTest`) y su uso;
  `.streamlit/config.toml`; `scripts/prueba_data_editor.py`, `scripts/medir_data_editor.md`; las 17 filas `ParTDD` con ruta `ui/` o
  `.streamlit/` de `scripts/meta_silice*.py` (`_primer_commit` usa `git log --diff-filter=A -- ruta`, que funciona con rutas
  borradas; confirmarlo corriendo la meta) y `CARPETAS_SIN_HTML_INSEGURO` (quitar `"ui"`).
- **Pruebas:** guardia de F1 ampliada con «`ui/paginas` no existe» y «ningún módulo importa `streamlit` ni `altair`» →
  rojo visto → borrar → verde. Reescribir `tests/unit/test_extras_perezosos.py` para importar `api.main` en lugar de `ui.app`
  (conserva INV-024: importar la aplicación no carga `ifcopenshell`, `ezdxf`, `sentence_transformers`).
- **Salida:** `rg -l "streamlit|altair" --glob "*.py"` vacío; suite verde; metas de la CI igual que en F0.
- **Riesgo:** medio-alto (volumen). Mitigación: borrar en commits por grupo (`paginas/` en 4 lotes, shell y sesión, utilidades,
  pruebas); cada commit deja la suite verde. **Revertir:** `git revert` por lote.
- **Secuencial** tras F2 y F3.

### F5 · Puentes `ui/<módulo>.py` → `aplicacion`
- **Objetivo:** las pruebas «MIGRAR» que no tocan la hoja importan de `aplicacion`; se borran los puentes (c).
- **Archivos:** `ui/{composicion,control,elaboracion,entrega,estilo,indices,precios_empresa,proyectos,reajuste,revision,subidas,tablero,atipicos}.py`;
  `ui/entorno.py` → `aplicacion/entorno.py` (mover `VARIABLE_CASO`, `ALIAS_ANTERIORES`, `leer_variable`; `tests/conftest.py:17`,
  `test_entorno_silice`, `test_aplicacion_entorno`, `test_nombre_silice` apuntan allí); pruebas `test_aplicacion_*`, `test_ui_{revision,subidas,
  indices,proyectos,reajuste,estilo_graficos}`, `integration/test_{entrega,revision_recibir,ui_control,composicion_*,atipicos}`.
  `ui.atipicos.avisos` (escape Markdown de Streamlit) se retira; `test_atipicos` se ajusta.
- **Pruebas (TDD):** guardia «`ui/` solo contiene `hoja.py`, `composicion.py` y `__init__.py`» → rojo visto → verde. Los
  `test_ui_*` de lógica pasan a `test_aplicacion_*` o se renombran (`git mv` en commit aparte para conservar historia).
- **Salida:** suite verde; `rg "from ui" tests` solo en archivos de la hoja (F6/F7).
- **Riesgo:** bajo (reexportaciones explícitas). **Revertir:** `git revert`.
- **Paralelo:** por módulo, sí (archivos de prueba disjuntos por nombre).

### F6 · Paridad → literales y oráculos `clasica`
- **Objetivo:** que ninguna prueba use `ui.hoja`/`ui.composicion` como oráculo; los 7 archivos de paridad (201 ítems) y los 9
  usos sueltos de `clasica` dejan de comparar contra la copia.
- **Hacer:** por prueba: si compara `aplicacion` vs `clasica` y ya hay literal asertado fuera (tabla §2.2) → se borra la mitad
  `clasica` o la prueba entera si era solo comparación (justificar en el commit); si no hay literal → se **reescribe** con el
  valor a mano de la memoria de OF-001 (`tests/fixtures/memorias/of001.md`), de TI-001 o de la fuente (ERS). Se conserva
  la tabla `TABLA_5_7` (cobertura por función pública; `test_aplicacion_hoja_paridad.py`) renombrada, porque protege que cada
  función de `aplicacion/hoja.py` tenga prueba. Se borra la prueba «el Plan C no toca nada congelado»
  (`test_aplicacion_hoja_paridad.py:149`).
- **Pruebas (TDD):** para cada prueba reescrita, **rojo visto** alterando temporalmente el valor literal (o la entrada) y
  comprobando que falla; después restaurar. Los archivos pasan a llamarse `test_aplicacion_hoja_*.py` (sin `paridad`).
- **Salida:** `rg "from ui" tests` → solo pruebas que prueban `ui.hoja` como sujeto (F7); aserciones de §2.2 siguen presentes.
- **Riesgo:** medio (aserción perdida o circular). Mitigación: el árbitro revisa A2 (oráculos independientes) con la tabla §2.2.
- **Secuencial** tras F5 (comparte archivos con F7); paralelo interno por archivo.

### F7 · Conmutación atómica de la hoja y prueba de equivalencia
- **Objetivo:** `asistente/` (auditor incluido), fixtures, pruebas y scripts pasan de `ui.hoja` a `aplicacion.hoja`; se prueba que
  la lógica del auditor no cambió.
- **Archivos (un solo commit lógico; tres commits si el árbitro lo pide: guardia / código / pruebas):**
  `asistente/{validacion,orquestador,privacidad,propuestas,servicio}.py`, `asistente/experimento/{banco,ejecucion}.py`;
  `tests/fixtures/{asistente_base,asistente_pedidos,hoja_borrador,hoja_en_base,versiones}.py` (fixtures que construyen `Borrador`);
  las pruebas restantes que importan `ui.hoja` como sujeto (≈ 40 archivos: `test_hoja*.py`, `test_asistente_*`, `test_experimento_*`,
  `test_caso_of001`, `test_responsables`, `test_seed_of001`, `integration/test_*hoja*`, …); `tests/unit/test_arquitectura_asistente.py`
  (las capas pasan a «`asistente` importa `aplicacion.hoja`, `aplicacion.errores`»); vaciar `PENDIENTES` de la guardia de F1.
- **Atomicidad:** mientras exista una prueba que cree `ui.hoja.Borrador` y la pase a `asistente/`, o al revés, hay dos clases
  distintas; por eso `asistente/`, los fixtures y las pruebas cambian juntos.
- **Pruebas (TDD):** (1) guardia: `PENDIENTES = ∅` → **rojo visto** (7 importadores); (2) correr el script de equivalencia
  (Apéndice A) contra `cd46732` → debe imprimir «EQUIVALENTE» para los 7 archivos de `asistente/`; (3) implementar.
  La equivalencia conductual es la suite del auditor + `calcular()["banco"] == congelado.json["banco"]`.
- **Salida:** suite verde (salvo el congelado); equivalencia pegada en la bitácora; `asistente/**` sin imports de `ui`.
- **Riesgo:** alto en proceso, bajo en lógica: se tocan 6 archivos congelados, pero solo líneas de import. Tentación a evitar:
  «arreglar» algo del auditor de paso (prohibido; cualquier otro diff devuelve el trabajo).
- **Revertir:** `git revert` de los commits de F7 en orden inverso. **Secuencial.**

### F8 · Borrar `ui/`
- **Objetivo:** el directorio `ui/` desaparece.
- **Archivos:** `ui/hoja.py`, `ui/composicion.py`, `ui/__init__.py`; `tests/unit/test_arquitectura.py`
  (quitar las tablas `PROHIBIDOS_EN_UI` y las comprobaciones de `ui/…`, añadir «no existe `ui/`» y «`aplicacion/` no importa
  `streamlit`»), `test_arquitectura_s1/s2/s3/s5` (ídem), `scripts/meta_prototipo.py` (P7 pasa a `aplicacion/composicion.py` o se
  marca retirada), `scripts/meta_silice.py` (pares TDD de `ui/entorno.py` y `.streamlit/config.toml` si no se quitaron en F4).
- **Pruebas:** guardia «no existe `ui/` ni `.streamlit/`» → rojo → verde; suite completa.
- **Riesgo:** bajo si F5–F7 cerraron. **Revertir:** `git revert`.

### F9 · Dependencias y empaque (compartido: `pyproject.toml`, `uv.lock`)
- **Objetivo:** el extra `ui` y sus 15 paquetes desaparecen sin romper la API.
- **Archivos:** `pyproject.toml` (quitar `ui = […]`; `known-first-party` sin `"ui"`; **añadir `python-multipart` al extra `api`**);
  `uv.lock` (`uv lock`; **si no hay red, no medido**: se pide a Eugenio o se corre en la CI); `instalador/manifiesto.toml` y
  `medir_capas.py` si F2 no lo hizo; comentario de extras de `pyproject.toml`.
- **Pruebas (TDD):** prueba nueva «las rutas con `File`/`Form` se importan en un entorno sin `ui`» (importar `api.main` sin
  `python-multipart` falla en FastAPI) → rojo visto en un entorno temporal sin ese paquete; `test_dependencias_silice`,
  `test_manifiesto`, `test_medir_capas`, `test_construir`; `uv sync --locked --all-extras` en limpio (CI).
  `docs/pip-audit-aceptadas.toml`: no apareció en el barrido de «streamlit», pero revisar avisos de los paquetes que salen.
- **Riesgo:** medio (versión de `python-multipart` fijada hoy solo por el lock). **Revertir:** `git revert` de `pyproject.toml`
  y `uv.lock` **juntos**.
- **Puede adelantarse** a justo después de F4 (ya nada importa Streamlit), con F2 hecho.

### F10 · Documentos vivos, contrato de la API y registro
- **Objetivo:** que lo vigente diga la verdad; `docs/api.json` coherente.
- **Archivos:** `README.md`, `NORMAS.md` (§6: árbol sin `ui/` ni `.streamlit/config.toml`; la línea de `tests/fixtures`),
  `docs/ERS.md` (enmienda: RT-4 y RF-81 cambian; RNF-11/15 se miden en `aplicacion.hoja`/`aplicacion.control`; **puede requerir
  aval del tutor si toca requisitos aprobados**, Q3), `docs/{arquitectura,manual_tecnico,manual_usuario,plan_pruebas,guion_prueba_arenia,metodologia,protocolo_indicador3}.md`,
  `docs/protocolo_asistente.md:110`, `scripts/README.md`, `frontend-desktop/{README,DESIGN,PRODUCT}.md`; código de superficie:
  `api/rutas/sesion.py` + `aplicacion/entorno.py` (quitar `url_clasica`), docstrings con «Streamlit» de `api/` y `aplicacion/`;
  `docs/api.json` regenerado; `CHANGELOG.md`; una bitácora de cierre en `docs/bitacora/`.
- **Frontend** (carril aparte, **requiere autorización** porque este encargo prohíbe tocarlo): `App.tsx`, `api/tipos.ts`,
  `shell/MenuLateral.tsx` (`PaginaSinMigrar`), `shell/rutas.ts` y sus pruebas, `VITE_URL_CLASICA`; `npm run lint/test/build`.
- **Pruebas:** `test_nombre_silice` (documentos vigentes), `meta_datos.py`, `app.openapi()==docs/api.json`, `test_api_acerca`/`test_api_sesion*`.
- **Riesgo:** bajo; el de contrato (campo `url_clasica`) es una baja: ningún cliente fuera de React lo usa (no medido fuera del
  repositorio). **Paralelo:** docs por carpeta disjunta; `NORMAS.md`/`CHANGELOG.md`/`docs/api.json` solo el orquestador.

### F11 · Re-congelado (commit aparte, el último)
- **Objetivo:** `test_experimento_congelado_vigente` en verde con las rutas definitivas (opción A).
- **Pasos (cada uno un commit, sin nada intercalado):**
  1. `asistente/experimento/protocolo.json`: `ui/hoja.py`→`aplicacion/hoja.py`, `ui/composicion.py`→`aplicacion/composicion.py`
     (± `aplicacion/errores.py`, Q4); asunto `docs(experimento): rutas definitivas del auditor tras retirar Streamlit`.
  2. `docs/protocolo_asistente.md` (línea del auditor) y la nota/ruling de Eugenio en `docs/bitacora/` (opción A, fecha 2026-10-21;
     si la decisión pasa por el tutor, anotar quién avaló).
  3. Árbol limpio (`git status --porcelain` vacío); regenerar con el comando de §3; verificar
     `uv run --active --no-sync python -c "from asistente.experimento import congelado; print(congelado.verificar())"` → `[]`;
     commit aparte de `congelado.json`; asunto `chore(asistente): re-congelar el experimento contra las rutas definitivas`.
- **Prueba:** `pytest tests/unit/test_experimento_congelado_vigente.py tests/unit/test_experimento_congelado.py -W error` verde.
- **Riesgo:** cualquier commit posterior que toque un archivo del auditor vuelve a rojo la guardia: **congelar el árbol del
  auditor** hasta fusionar. **Revertir:** `git revert` del commit de `congelado.json` (vuelve a la huella vieja → rojo conocido).

---

## 5. Paralelismo, rutas compartidas y dueños

| Carril | Fases | Carpetas (disjuntas) |
|---|---|---|
| A · Producto | F2 | `operacion/`, `instalador/`, `start.py`, `.github/workflows/instalador.yml`, pruebas de lanzador/manifiesto/ajustes |
| B · Pruebas de `ui` | F3 → F4 (borrado), luego F5 | `tests/unit/test_ui_*`, `ui/` |
| C · Hoja y auditor | F6 → F7 → F8 → F11 | `tests/unit/test_aplicacion_hoja*`, `test_api_hoja*`, `asistente/`, fixtures de la hoja |
| D · Dependencias | F9 | `pyproject.toml`, `uv.lock` |
| E · Documentos y frontend | F10 | `docs/`, `README.md`, `frontend-desktop/` (autorizado aparte) |

Paralelo seguro: **A ‖ B(F3)** y, tras F4, **F5 ‖ D(F9)**; F10 por carpeta. **Secuencial**: F1 → (F2 y F3) → F4 → F5 → F6 → F7 → F8 → F11.
F6 y F7 comparten ≈ 14 archivos de prueba: un solo dueño (carril C). F5 y F6 comparten `test_ui_reajuste.py`/`test_ui_proyectos.py`
(importan `hoja` y otro puente): los reescribe F6.

Rutas **compartidas** y su dueño (nadie más las edita; los demás piden la línea al dueño):

| Ruta | Dueño | Cuándo |
|---|---|---|
| `pyproject.toml`, `uv.lock` | carril D (F9); F2 solo si el instalador exige un cambio, avisando a D | F9 |
| `CHANGELOG.md` | orquestador (una línea por fase, con las que entreguen los implementadores) | al cerrar cada fase |
| `NORMAS.md`, `docs/ERS.md` | orquestador/Eugenio (F10); el ERS toca requisitos | F10 |
| `docs/api.json` | quien cambie `api/` (F10), regenerado en el mismo commit | F10 |
| `tests/conftest.py` | carril B: AppTest (F4) y entorno (F5), en commits separados | F4, F5 |
| `scripts/meta_*.py` | carril B (F4/F8) | F4, F8 |
| `asistente/experimento/protocolo.json`, `congelado.json` | solo F11 | F11 |

---

## 6. Comandos de verificación por tanda

Entorno común (PowerShell; **`SILICE_DATOS` temporal antes de importar el proyecto**, nada se escribe en `data/`):

```powershell
$d = Join-Path $env:TEMP ("silice-" + [guid]::NewGuid()); New-Item -ItemType Directory $d | Out-Null
$env:SILICE_DATOS = $d
$env:PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring'
$env:VIRTUAL_ENV = 'C:\Users\euger\OneDrive\Escritorio\TESIS\.venv'
uv run --active --no-sync pytest <archivos> -q -W error -p no:cacheprovider
uv run --active --no-sync ruff check <archivos>
```

- **Cierre de fase:** `pytest -W error -p no:cacheprovider` completo (con `--junitxml=reporte-pruebas.xml` y
  `scripts/verificar_omitidas.py reporte-pruebas.xml`: cero omitidas), `ruff check .`, y las metas de la CI
  (`scripts/meta_silice.py --version 0.6.0 --hasta S1-5 --junit …` y `--version 0.7.0 --hasta S2-2`). Una corrida de
  `--collect-only` sobre toda la suite tardó más de 2 minutos aquí: correr en segundo plano.
- **Esperado:** todo verde salvo `tests/unit/test_experimento_congelado_vigente.py` (rojo conocido hasta F11). El conteo de
  ítems baja en F3–F4 (−658 de AppTest, −46 retirados, ± lo movido): registrar `pytest --collect-only -q` antes y después.
- **Contrato de la API** (si cambia `api/`): `uv run --active --no-sync python scripts/exportar_openapi.py` y
  `git diff --exit-code -- docs/api.json`; la comparación sin escribir:
  `uv run --active --no-sync python -c "import json,pathlib; from api.main import app; assert app.openapi()==json.loads(pathlib.Path('docs/api.json').read_text(encoding='utf-8')); print('OK')"`.
- **Guardias propias de este plan:** `tests/unit/test_arquitectura_retiro.py` (F1, ampliada en F4, F5, F7, F8).
- **Frontend** (solo F10, autorizado): `npm run lint`, `npm test`, `npm run build` en `frontend-desktop`.
- **Congelado:** `uv run --active --no-sync python -c "from asistente.experimento import congelado; print(congelado.verificar())"`.
- **Para el árbitro** (Manual del árbitro §1): solo lectura; `core/` intacto (`git diff <base>..HEAD -- core/` vacío) en todas las
  fases; revisa A2 (oráculos independientes) en F6 y B2 (DRY) en F5/F7.

---

## 7. Riesgos reales

1. **Producto sin interfaz (F2).** Streamlit es hoy el proceso principal del lanzador; ver §0. Mitigación: F2 antes de F4; F4 no se
   integra sin F2. «Modo entrega» (`SILICE_MODO_ENTREGA`) lo respeta `aplicacion/entorno.py` y `api/`; confirmar con Eugenio que la
   navegación de React lo esconde igual (no medido).
2. **`python-multipart`** (§0.2). Una subida rota solo se vería al importar la ruta: la prueba de F9 lo cubre.
3. **Asistente de IA de la Hoja sin interfaz** (§0.3, Q2). Las pruebas `test_ui_hoja_asistente.py` (20) se borran; `asistente/servicio.py`
   queda con pruebas de lógica pero sin llamador de producción. `docs/planes/PLAN_MIGRACION_FINAL_STREAMLIT.md` ya decía que el
   panel «no se migra».
4. **Dos `Borrador`** → conmutación atómica (F7).
5. **Scripts de la tesis y del experimento** que usan `ui.*` (los 5 de F1) y los que viajan en el instalador
   (`manifiesto.toml: cierre_desde = scripts.seed_of001, …`): si `seed_of001` siguiera importando `ui`, el instalador no
   arrancaría tras quitar el paquete `ui`. F1 lo cubre; F2 quita `"ui"` de `paquetes` (verificar con `test_manifiesto`).
6. **Instalador.** No usa PyInstaller: copia CPython autónomo + `uv` y capas de extras (`instalador/manifiesto.toml`); la capa `ui`
   desaparece y el instalador adelgaza (tamaños: no medido). El humo del instalador (`humo.ps1`) solo corre en la CI de Windows.
7. **Metas de la CI.** `meta_silice` exige pares TDD de `ui/…`; `_primer_commit` usa historia, pero otras metas (`meta_prototipo` P7,
   `meta_silice_s3` S3-M3) leen el árbol: correrlas en F4 y F8 y ajustarlas; «no medido» cuál queda en rojo.
8. **Docs de tesis y bitácora que citan Streamlit** son historia: no se reescriben. `test_nombre_silice` y `meta_datos.py` recorren
   documentos «vigentes»; si una guardia recorre historia, se ajusta la guardia.
9. **Datos reales.** Nada de lo anterior toca datos; los fixtures son ficticios. En F6 los oráculos salen de la memoria **ficticia**
   `tests/fixtures/memorias/of001.md`. Prohibido, en cualquier fase, copiar libros o nombres de empresa reales como oráculo.
10. **Guardia del congelado rota durante 11 fases.** Aceptado y declarado; el riesgo es olvidarse y fusionar a `main` con la guardia
    roja (la CI de `main` quedaría en rojo): **no se fusiona antes de F11**.
11. **Tocar el auditor de paso.** Cualquier cambio de lógica en `asistente/` durante F7 invalida el re-congelado «por equivalencia».
12. **Frontend.** `VITE_URL_CLASICA` y `PaginaSinMigrar` quedan como código muerto hasta el carril E; no afectan a la API.

---

## 8. Preguntas abiertas para Eugenio

- **Q1 (F2).** ¿Un solo proceso Uvicorn con `/app` y un único puerto? ¿Qué pasa con `[api] activa` y con los `silice.toml` ya
  escritos con `puerto = 8501`? (propuesta: se respeta `[servidor] puerto` como puerto de todo y `[api] activa` se ignora con aviso).
- **Q2.** El asistente de IA de la Hoja no existe en React. ¿Se construye antes del retiro, o se acepta que quede sin interfaz
  (y se anota como limitación)?
- **Q3.** El ERS dice «Streamlit sigue siendo la principal (RT-4)» y fija RF-81/RNF-11/RNF-15 sobre `ui.*`: ¿la enmienda necesita
  aval del tutor, o basta tu ruling?
- **Q4.** ¿Qué archivos son «el auditor» tras el cambio? Mínimo: `aplicacion/hoja.py` y `aplicacion/composicion.py` (esta ya
  incluye 20 definiciones nuevas). ¿Se añade `aplicacion/errores.py` (donde está `HojaInvalida`)?
- **Q5.** ¿Se sube la versión (`pyproject.toml` dice 1.2.0) y se etiqueta al fusionar, o el retiro es parte de la 1.2.x?
- **Q6.** ¿Se acepta que `docs/api.json` pierda `url_clasica` (contrato de la API, solo lo consume el menú de React)?
- **Q7.** La paridad pantalla por pantalla Streamlit → React no la verifica este plan: ¿la prueba de navegador de Eugenio es la
  compuerta de F4?

---

## Apéndice A · Script de equivalencia (efímero; se corre en F7)

Normaliza `ui`→`aplicacion` en los nodos de importación, quita docstrings y compara definiciones por `ast.dump`. Se ejecuta con
`python -I` (sin cargar el proyecto) sobre el contenido de `git show cd46732:<ruta>` guardado en un archivo temporal del
scratchpad (**no** en una carpeta que contenga un `ast.py` u otro módulo homónimo de la biblioteca estándar) y la versión de HEAD:

```python
import ast, sys
from pathlib import Path

def norm(p):
    t = ast.parse(Path(p).read_text(encoding="utf-8"))
    class N(ast.NodeTransformer):
        def visit_ImportFrom(self, n):
            if n.level == 0 and n.module and n.module.startswith("ui"):
                n.module = "aplicacion" + n.module[2:]
            return n
        def visit_Import(self, n):
            for a in n.names:
                if a.name.startswith("ui."):
                    a.name = "aplicacion" + a.name[2:]
            return n
    t = N().visit(t)
    for n in ast.walk(t):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body \
           and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant) \
           and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return t

def partes(t):
    defs = {n.name: ast.dump(n) for n in t.body if hasattr(n, "name")}
    resto = sorted(ast.dump(n) for n in t.body if not hasattr(n, "name"))
    return defs, resto

a, b = norm(sys.argv[1]), norm(sys.argv[2])       # congelado, HEAD
da, ra = partes(a); db, rb = partes(b)
print("solo en congelado:", sorted(set(da) - set(db)))
print("solo en HEAD:", sorted(set(db) - set(da)))
print("definiciones distintas:", sorted(k for k in da if k in db and da[k] != db[k]))
print("EQUIVALENTE" if da == db and ra == rb else "DIFERENTE")
```

Resultados medidos hoy (para contrastar en F7; se obtuvieron con una variante de este script que además compara importaciones):
`cd46732:ui/hoja.py` vs `aplicacion/hoja.py` → «solo en congelado: [HojaInvalida]», `distintos: []`, asignaciones iguales;
`cd46732:ui/composicion.py` vs `aplicacion/composicion.py` → `distintos: []`, 20 definiciones solo en HEAD (por eso en F7 el
criterio 3 es «⊇», no «=»: el script de arriba imprimirá «DIFERENTE» para ese par y se interpreta con la lista «solo en HEAD»).
Los 7 archivos de `asistente/` aún importan `ui`; su normalización se prueba en F7 (esperado: «EQUIVALENTE»; si el único
cambio es el comentario de `propuestas.py:45`, queda fuera del AST y no cuenta).
