# PLAN_SF — sprint final del prototipo (hoja del proyecto, metrajes, edición trazable, barra superior)

> **Para quien ejecute:** usar `superpowers:subagent-driven-development` (elegido por Eugenio el
> 2026‑10‑04: subagentes en un worktree). Los pasos usan casillas `- [ ]`.

**Meta:** que un usuario levante el espacio de una oficina (o importe un plano), obtenga el presupuesto
auditado de agua, datos y electricidad, edite una línea con recálculo y registro de cambios, y exporte
el Excel, todo dentro del sistema.

**Arquitectura:** `adapters/espacio` (nuevo) deriva cantidades desde un modelo espacial versionado;
siete expedientes genéricos en `core/` (SF‑E1 a SF‑E7) dan edición, versiones, punto de equilibrio,
Excel y origen de precios; `ui/hoja.py` orquesta y la pantalla nueva con barra superior lo muestra.

**Tecnología:** Python 3.13, `uv`, SQLAlchemy, Streamlit ≥ 1.62, `ezdxf` (extra `planos`),
`ifcopenshell` (extra `civil`), openpyxl, evaluador de fórmulas en el grupo `dev`.

**Spec:** [docs/especificaciones/2026-10-04-sprint-final-prototipo-design.md](docs/especificaciones/2026-10-04-sprint-final-prototipo-design.md)
(revisión 3). Este plan **no repite** el spec: lo enlaza por sección (`spec §n`).

## Restricciones globales (del spec y de NORMAS.md)

- `Decimal` en todo lo monetario y dimensional; redondear solo al presentar (NORMAS §2.3).
- `adapters/` solo importa `core.contracts` (más `sqlalchemy`, `ezdxf`, `ifcopenshell` en `espacio`).
- Pruebas antes que código, **con el rojo observado**: el commit de la prueba va antes que el de la
  implementación (spec §12.1).
- Commits convencionales en español sin tildes en el asunto; terminan con la línea
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Una rama de **núcleo** (`inc/sf<n>-nucleo`, solo `core/`) se fusiona antes que la rama del adaptador
  (`inc/sf<n>`, sin `core/`): `scripts/guardia_nucleo.py` y M9 lo exigen (spec §12.2).
- Nunca escribir en `data/apu.db`; las pruebas con base usan archivos temporales o `data/prueba_sf.db`.
- Suite con `-W error`, 0 omitidas, Linux y Windows. Cobertura de `core/` ≥ 80 %.
- Cada fase termina con: `uv run python scripts/meta_sf.py --hasta SF<n>` en OK, CI verde, los cuatro
  encargos de revisión aprobados y la compuerta anotada en `docs/bitacora/2026-10-sf.md`.

## Foco de revisión (casos que el spec implica y ninguna tarea cubriría sola)

1. Un proyecto sin ningún ambiente ni punto: la hoja abre vacía, no falla; `derivar` devuelve `[]`.
2. Un punto sin recorrido y una fuente sin puntos: no hay división por cero ni tramos de largo cero.
3. Dos recorridos que comparten un tramo parcial colineal: la tubería no se cuenta dos veces.
4. Guardar dos veces seguidas sin cambios: no crea una versión vacía ni `RegistroCambio` falsos.
5. Abrir una versión de la clínica o de TI‑001 (sin instantánea, sin espacio): la hoja abre y marca la
   instantánea creada (spec UC‑15e); nada se rompe.

Cada línea tiene su prueba en la tarea dueña (marcadas **[FR‑n]** abajo).

---

## Cómo se ejecuta

1. Fusionar primero la rama `inc/spec-sf` (spec + este plan) a `main` por PR, con la CI verde.
2. Crear la etiqueta `sf-base` en ese `main` y el worktree: `git worktree add .worktrees/sf -b inc/sf0 main`.
3. Por fase: un subagente por tarea con revisor fresco; al cerrar la fase, los cuatro encargos de
   revisión (spec §12.2). Los expedientes de `core/` esperan el visto bueno del tutor antes de fusionar
   (spec §12.3); si no llega, la fase se entrega sin esa pieza y se declara.
4. **Este archivo detalla paso a paso SF0.** SF1 a SF5 se detallan al cruzar la compuerta anterior,
   igual que `PLAN_CIERRE.md`: lo que sí fijan desde ya son archivos, interfaces y pruebas por tarea,
   para que ninguna fase dependa de adivinar nombres.

---

# SF0 — Documentos, fuentes y prueba corta (rama `inc/sf0`)

### Tarea 0.1: Meta del sprint, `scripts/meta_sf.py`

**Archivos:**
- Crear: `scripts/meta_sf.py`, `tests/unit/test_meta_sf.py`

**Interfaces:**
- Consume de `scripts/meta_alpha.py`: `Estado`, `Fila`, `_filas_a_json`, `render_tabla`.
- Produce: `FASES: dict[str, tuple[str, ...]]` con claves `SF0`…`SF5`; `metas_hasta(fase: str) -> list[str]`;
  `evaluar_s1_requisitos(texto_ers: str | None) -> tuple[Estado, str]`; `main(argv) -> int`.

- [ ] **Paso 1: prueba que falla**

```python
# tests/unit/test_meta_sf.py
from scripts.meta_alpha import Estado
from scripts.meta_sf import FASES, evaluar_s1_requisitos, metas_hasta


def test_metas_hasta_acumula_fases_en_orden():
    assert metas_hasta("SF0") == list(FASES["SF0"])
    assert set(FASES["SF0"]) <= set(metas_hasta("SF3"))


def test_s1_ok_con_todos_los_uc_y_rf_nuevos():
    ers = " ".join(f"UC‑{n}" for n in range(13, 17)) + " " + " ".join(f"RF‑{n}" for n in range(44, 64))
    ers += " RNF‑11 RNF‑12 RNF‑13"
    estado, _ = evaluar_s1_requisitos(ers)
    assert estado is Estado.OK


def test_s1_falla_si_falta_un_requisito_y_pendiente_sin_ers():
    assert evaluar_s1_requisitos("UC‑13")[0] is Estado.FALLA
    assert evaluar_s1_requisitos(None)[0] is Estado.PENDIENTE
```

- [ ] **Paso 2: verlo fallar** — `uv run pytest tests/unit/test_meta_sf.py -v` → `ModuleNotFoundError: scripts.meta_sf`.
- [ ] **Paso 3: implementar** `meta_sf.py` siguiendo la forma de `scripts/meta_prototipo.py` (tabla
  `FASES`/`TITULOS`, funciones `evaluar_*` puras, `_evaluar_metas`, `main` con `--hasta` y `--json`).
  Las metas S1–S10 y su fase de arranque están en spec §12.2; lo no construido da `PENDIENTE`.
  `evaluar_s1_requisitos` busca con el patrón `[-‑]` (guion normal o no separable) cada uno de
  UC‑13…UC‑16, RF‑44…RF‑63, RNF‑11…RNF‑13.
- [ ] **Paso 4: verlo pasar** — `uv run pytest tests/unit/test_meta_sf.py -v` → PASS.
- [ ] **Paso 5: commit** — `git add scripts/meta_sf.py tests/unit/test_meta_sf.py` /
  `feat(scripts): meta del sprint final con S1 de requisitos`.

### Tarea 0.2: Enmienda de la ERS (IEEE 830)

**Archivos:**
- Modificar: `docs/ERS.md` (tabla de actores §2.3; UC‑01 paso 1; §2.4, §2.5, §2.6; RF‑37, RF‑39, RF‑42;
  nota de UC‑09 en las líneas 22‑26 y 589‑590; conteos «42 RF» y «once casos de uso»; RNF‑11 a RNF‑13)

**Interfaces:** produce UC‑13 a UC‑16, RF‑44 a RF‑63 y RNF‑11 a RNF‑13 tal como están en spec §4 (la
fuente única; copiarlos con sus columnas de prioridad, fase y criterio, no resumirlos).

- [ ] **Paso 1:** correr `uv run python scripts/meta_sf.py --hasta SF0` → S1 FALLA (prueba roja).
- [ ] **Paso 2:** escribir cada UC completo (actor, precondición, flujo principal, alternos, postcondición)
  desde la tabla de spec §4.1; los RF y RNF desde §4.2 y §4.3; agregar el actor «gerente».
- [ ] **Paso 3:** actualizar conteos (62 RF, quince UC), la reserva de UC‑09 (pasa a RF‑64), UC‑01 paso 1
  (la interfaz crea proyectos, RF‑63), §2.4 y §2.6 (DXF e IFC2x3 e IFC 4 como entradas), RF‑39 (once
  pantallas) y RF‑37/RF‑42 (orden del menú y recorridos).
- [ ] **Paso 4:** `uv run python scripts/meta_sf.py --hasta SF0` → S1 OK; `uv run pytest -W error -q` verde.
- [ ] **Paso 5: commit** — `docs(ers): enmienda del sprint final (UC-13 a UC-16, RF-44 a RF-63)`.

### Tarea 0.3: Arquitectura, modelo de datos, plan de pruebas y NORMAS

**Archivos:**
- Modificar: `docs/arquitectura.md`, `docs/modelo_datos.md` (líneas 20, 209 y 625‑630), `docs/plan_pruebas.md`
  (§8, §8.1, §9, filas para RF‑44 a RF‑63 y RNF‑11 a RNF‑13), `NORMAS.md` §6 (conteo de entidades y
  estructura de carpetas), `core/models/base.py:9` (solo el docstring se enmienda en SF3, no aquí)

- [ ] **Paso 1:** registrar en `arquitectura.md` las vistas del spec §5 (paquetes, proceso de una edición,
  desarrollo y despliegue) y las decisiones DA‑SF‑1 a DA‑SF‑9.
- [ ] **Paso 2:** en `modelo_datos.md` añadir `RegistroCambio`, la instantánea de composiciones, las tablas
  `esp_*` y los campos de SF‑E7; **reemplazar** la frase «no afecta a los presupuestos emitidos»
  (línea 625‑630) por la corrección del spec §1.2.
- [ ] **Paso 3:** en `plan_pruebas.md` añadir las filas de trazabilidad RF → prueba de spec §11.2, los
  pasos de UC‑13 a UC‑16 en §8.1 y RNF‑11 a RNF‑13 en §9.
- [ ] **Paso 4:** `uv run pytest -W error -q` verde (hay pruebas que leen estos documentos).
- [ ] **Paso 5: commit** — `docs(arquitectura): vistas, modelo de datos y plan de pruebas del sprint final`.

### Tarea 0.4: Fuentes normativas, licencia de ezdxf y clases IFC

**Archivos:**
- Modificar: `docs/tesis/referencias.md` (fuentes de spec §7 con estado verificado o «supuesto»)
- Crear: `docs/bitacora/2026-10-sf.md` (bitácora del sprint)

- [ ] **Paso 1:** para cada fuente candidata (Gaceta 4.044, COVENIN/FONDONORMA 200, ANSI/TIA‑568) seguir
  el procedimiento de `docs/tesis/referencias.md`: verificada → registrar cita y valor de la
  constante; no verificada → registrar «supuesto declarado» (RS‑5). Una sola denominación para la
  norma eléctrica.
- [ ] **Paso 2:** confirmar en PyPI la licencia de `ezdxf` y anotarla en la bitácora.
- [ ] **Paso 3:** fijar con dos IFC de prueba (IFC2x3 e IFC4, procedencia declarada) las clases exactas
  de espacios, terminales y tableros de spec §6.6.2 y anotarlas en la bitácora.
- [ ] **Paso 4:** abrir en `docs/auditoria/2026-09-inventario.md` los hallazgos nuevos A‑1, A‑2, M‑1, M‑2
  y M‑3 con severidad y fase de corrección (spec §8.3).
- [ ] **Paso 5: commit** — `docs(referencias): fuentes del sprint final y hallazgos nuevos del inventario`.

### Tarea 0.5: Generador de 500 puntos y prueba corta de `st.data_editor`

**Archivos:**
- Crear: `scripts/generar_hoja_prueba.py`, `tests/unit/test_generar_hoja_prueba.py`,
  `scripts/prueba_data_editor.py` (app Streamlit descartable)

**Interfaces:** produce `generar_items(n: int, semilla: int = 0) -> list[ItemComputo]`, determinista
(misma semilla → mismos ítems), que también usará `medir_rnf11.py` en SF3.

- [ ] **Paso 1: prueba que falla**

```python
# tests/unit/test_generar_hoja_prueba.py
from scripts.generar_hoja_prueba import generar_items


def test_generador_es_determinista_y_del_tamano_pedido():
    a = generar_items(500, semilla=7)
    b = generar_items(500, semilla=7)
    assert len(a) == 500
    assert a == b
    assert generar_items(500, semilla=8) != a
```

- [ ] **Paso 2: verlo fallar** — `uv run pytest tests/unit/test_generar_hoja_prueba.py -v` → ModuleNotFoundError.
- [ ] **Paso 3: implementar** el generador con `random.Random(semilla)`, cantidades `Decimal`, `origen_tipo`
  `MANUAL`, `origen_id` `f"gen-{i}"`, dominio `CIVIL`.
- [ ] **Paso 4: verlo pasar** — PASS.
- [ ] **Paso 5:** escribir `scripts/prueba_data_editor.py`: `st.data_editor` con los 500 ítems, columna Estado
  aparte (otro `st.dataframe` o columnas de solo lectura fuera del editor), ediciones guardadas en
  `st.session_state["borrador_prueba"]` (clave que no es de widget), pestaña activa con
  `st.segmented_control`, y registro en un archivo de las marcas de tiempo de cada edición recibida y
  de cada Estado pintado; el cálculo sustituto de cada edición es `core.budget.elaborar` (spec §11.3).
- [ ] **Paso 6:** ejecutar el procedimiento de spec §11.3 en el navegador (20 ediciones de celda, 5 altas y
  5 bajas, una ordenación, 10 ediciones rápidas durante el reinicio) y anotar en la bitácora el
  veredicto PASA/FALLA con las marcas. Si FALLA: decisión DA‑SF‑1 → AG Grid (`streamlit-aggrid`), y las
  tareas 3.x de la hoja lo reflejan.
- [ ] **Paso 7: commit** — `test(scripts): generador de 500 puntos y prueba corta del editor de tablas`.

### Tarea 0.6: Cierre de SF0

- [ ] **Paso 1:** `uv run ruff check . && uv run pytest -W error -q && uv run python scripts/meta_sf.py --hasta SF0`.
- [ ] **Paso 2:** despachar los cuatro encargos de revisión (spec §12.2) sobre los documentos de SF0.
- [ ] **Paso 3:** PR `inc/sf0` → `main`, CI verde, fusión por *merge commit*; etiqueta `gsf0`; anotar GSF0 en
  la bitácora y abrir SF1.

---

# SF1 — Núcleo SF‑E1/E5 + adaptador de espacio con agua (ramas `inc/sf1-nucleo`, `inc/sf1`)

Detalle paso a paso al cruzar GSF0. Tareas, archivos, interfaces y pruebas ya fijados:

**1.0 (antes de cualquier código)** Versionar `tests/fixtures/memorias/bano_of001.md`: memoria de cálculo a
mano del baño de OF‑001 (un ambiente, una fuente, dos puntos de agua) con longitudes, unión de segmentos,
codos, tees, cajas y cantidades; con el dibujo del conteo de spec §6.5. Es el oráculo de 1.2 a 1.5.

**Rama de núcleo `inc/sf1-nucleo` (solo `core/`):**
- **1.1 SF‑E1** — `core/budget/presupuesto.py`: `elaborar(..., reglas: Sequence[ReglaVerificacion] = REGLAS)`;
  `core/budget/persistencia.py`, `actualizacion.py`, `escenarios.py`, `importacion.py`: re‑declarar los hallazgos
  guardados cuya regla no está en `REGLAS` (precedente `CODIGO_ATIPICO`, C6.5). Pruebas: informe recargado =
  emitido en cada camino **[FR‑4: guardar dos veces no duplica]**. Expediente en `docs/bitacora/2026-10-sf.md`.
- **1.2 SF‑E5** — `core/verification/reglas.py`: R4 compara especificaciones normalizadas y excluye del corpus
  la descripción del propio ítem. Pruebas: caso directo de `docs/linea_base.md`, los cuatro pares de la
  bitácora de TI‑001, `test_auditoria_7_de_7.py` y `test_r4_marca_3_4_pulg_y_no_marca_pvc` sin modificarse,
  huellas de RNF‑04 (si cambian, ruling de reanclaje).

**Rama de adaptador `inc/sf1` (sin `core/`):**
- **1.3** `adapters/espacio/modelo.py` + `persistencia.py` (`crear_esquema_espacio()`, tablas `esp_*` con clave
  de versión, §6.2) + `origen.py` (tipos y referencias de §6.3). Interfaz:
  `derivar(espacio: Espacio, especialidad: str) -> list[ItemComputo]`. **[FR‑1: espacio vacío → `[]`]**
- **1.4** `adapters/espacio/geometria.py`: recorrido propuesto (§6.4), unión de segmentos con partición de
  solapes colineales, clave de segmento, conteo de codos y tees (§6.5). Pruebas contra `bano_of001.md` a
  ±0,001 m **[FR‑2, FR‑3]**.
- **1.5** `adapters/espacio/especialidades/agua.py`: partidas derivadas de §7.1 con constantes y fuente.
- **1.6** `adapters/espacio/reglas.py`: R8 y R9 (instantánea del espacio, §8.2), un error sembrado por condición
  y valores frontera; OF‑001 limpio da el conjunto exacto de hallazgos esperado.
- **1.7** `tests/unit/test_arquitectura.py`: `TERCEROS_POR_ADAPTADOR["espacio"]`, `PROHIBIDOS_EN_UI` para
  `ui/hoja.py`. Meta S10 (cobertura ≥ 80 %) en la CI.
- **1.8** `ui/hoja.py` (sin Streamlit): borrador, derivación y elaboración con `reglas=REGLAS + reglas_espacio`;
  `ui/paginas/hoja.py`: pestaña Espacio y metrajes. **[FR‑5: abrir clínica/TI‑001 no rompe]**
- **Compuerta GSF1:** el baño de OF‑001 se levanta a mano y sale su presupuesto auditado.

# SF2 — Datos y electricidad, sin tocar `core/` (rama `inc/sf2`)

- **2.0** `tests/fixtures/memorias/of001.md` (oficina completa) antes del código.
- **2.1** `especialidades/datos.py` (§7.2) y `especialidades/electricidad.py` (§7.3, recorrido por circuito y
  cadena por vecino más cercano, editable).
- **2.2** R10 (§8.2): fronteras 90,00 m / 90,01 m, puntos por circuito y su máximo + 1, pendiente mínima.
- **2.3** M‑3: `adapters/telecom/adaptador.py` deja de emitir `origen`/`destino` como especificaciones; adenda a
  la bitácora de TI‑001 y ajuste de `test_auditoria_cumple_sin_errores`.
- **2.4** OF‑001 completo en `tests/fixtures/caso_of001.py` con precios MaPreX y su conjunto exacto de hallazgos.
- **Compuerta GSF2:** `git diff gsf1..HEAD -- core/` vacío (meta S4).

# SF3 — Núcleo SF‑E2/E3/E4/E6/E7 + hoja completa (ramas `inc/sf3-nucleo`, `inc/sf3`)

Núcleo (cada uno con expediente, prueba roja primero y visto bueno del tutor):
- **3.1 SF‑E6** instantánea de composiciones y rendimientos por versión; recarga, revaloración y escenarios la
  usan (catálogo solo para versiones anteriores).
- **3.2 SF‑E2** `core/budget/edicion.py` + `RegistroCambio` + `version_origen` + restaurar + versión vigente.
- **3.3 SF‑E3** `core/budget/equilibrio.py`: `punto_equilibrio(presupuesto, parametros)`; literales de TI‑001
  (28 586,76 USD, 56,60 %, Día 6) como oráculo; casos límite de §9.4; `scripts/analisis_ti001.py` lo importa.
- **3.4 SF‑E4** `core/budget/excel.py`: `exportar_hoja` + `TablaExportable`; M‑1 en las dos exportaciones;
  `exportar_excel` conserva sus cuatro hojas; `SUM`/`ROUND` en inglés; evaluador de fórmulas en `dev`.
- **3.5 SF‑E7** origen de precios y listas de proyecto; `lista_vigente` las excluye; cotización prevalece.

Hoja:
- **3.6** pestañas APU, Presupuesto, Plan y curva, Punto de equilibrio, Precios, Parámetros, Auditoría y
  Trazabilidad; columna Estado aparte; guardado en una sola `Session`; espacio heredado por `version_origen`.
- **3.7** `scripts/medir_rnf11.py` (calentamiento + mediana de cinco, registro en CI sin romper) y la cifra en
  `plan_pruebas.md §10`.
- **Compuerta GSF3:** editar una línea → recálculo → guardar con registro → restaurar → exportar.

# SF4 — Barra superior y cierre de interfaz (rama `inc/sf4`)

- **4.1** `ui/barra.py` y `ui/app.py` con `st.navigation(position="top")`, `streamlit>=1.62` en `pyproject.toml`
  y prueba que falla con una versión vieja; once pantallas, RF‑37/39/42 y recorridos de UC‑12.
- **4.2** Herramientas: Proyecto (RF‑63), Importar plano (oculta si SF5 cae), Precios, Auditar, Guardar versión,
  Exportar Excel, Recorrido guiado; AppTest de cada una y del modo entrega.
- **4.3** A‑1: una función de guardado seguro para `UploadedFile` en `actualizacion`, `elaborar` y `visor`;
  pruebas de `..\`, `../`, ruta absoluta y nombres reservados de Windows.
- **4.4** Manuales de usuario y técnico. Revisión adicional de usabilidad (Nielsen, ISO 9241‑110).

# SF5 — Importación de planos (rama `inc/sf5`, sin `core/`)

- **5.1** `adapters/espacio/planos/dxf.py` (ezdxf, convención de §6.6.1, `$INSUNITS`, límite de 20 MB,
  reimportación por *handle*) y el DXF de OF‑001 dibujado de forma independiente.
- **5.2** `planos/ifc.py` (IFC2x3/IFC4, informe, reimportación por `GlobalId`; duplica lo necesario de
  `adapters/civil/ifc.py`).
- **5.3** Informe de importación y herramienta «Importar plano»; S7.
- **5.4** Actualizar el guion (CP‑07 a CP‑11) y los pasos de los dos protocolos de Med **una sola vez** (spec §2).
- **Compuerta GSF5:** el DXF de OF‑001 da las mismas cantidades que la hoja a ±0,001 m; `git diff gsf4..HEAD -- core/` vacío.

---

## Autorrevisión contra el spec

- **Cobertura:** RF‑44…RF‑63 → tareas 1.3–1.6 (44–47, 61), 2.1 (48–49), 5.1–5.2 (50–51), 3.2 (53–54), 3.6
  (52, 55, 57), 3.5 (56), 3.3 (58), 3.4 (59), 4.1–4.2 (60, 63), 1.1 (62). RNF‑11 → 3.7; RNF‑12 → 3.4 y 4.3;
  RNF‑13 → Med. Hallazgos A‑1 → 4.3; A‑2 → 1.2; M‑1/M‑2 → 3.4; M‑3 → 2.3.
- **Sin completar a propósito:** el paso a paso de SF1 a SF5 se redacta al cruzar la compuerta anterior,
  porque depende de lo que SF0 decida (AG Grid o no, fuentes verificadas); sus archivos, interfaces y pruebas
  ya están fijados arriba.
