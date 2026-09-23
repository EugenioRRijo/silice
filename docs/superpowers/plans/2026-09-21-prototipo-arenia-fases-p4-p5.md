# AREN.IA — fases P4 y P5: pruebas de interfaz, siembra, corpus en cuarentena y cierre

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Dar al repositorio sus primeras pruebas automatizadas de interfaz, dejar la aplicación
lista para abrirse con un solo comando y con un guion de prueba manual, generar un corpus simulado
que no pueda contaminar `ml/`, y cerrar el sprint del prototipo con modo entrega, manuales y
bitácora: meta del sprint en **12/12**.

**Architecture:** Nada de esto inventa cálculo ni toca el núcleo. Las pruebas de interfaz conducen
`ui/paginas/componer.py` con `streamlit.testing.v1.AppTest` sembrando sus tablas por
`st.session_state`, porque `AppTest` no puede teclear en un `st.data_editor`. La siembra y el corpus
son scripts que reutilizan las funciones puras de `ui/composicion.py` y el `Catalogo`. El modo
entrega es un filtro puro sobre la lista de páginas de `ui/app.py`.

**Tech Stack:** Python 3.12 · `Decimal` · Streamlit 1.62.0 (`AppTest`) · SQLAlchemy 2 · pytest ·
ruff · uv

**Spec:**
[docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md](../specs/2026-09-16-prototipo-composicion-apu-design.md)
(§6 pruebas y criterios de aceptación, §8 riesgos y degradación).

**Plan de sesiones:** [PLAN_PROTOTIPO.md](../../../PLAN_PROTOTIPO.md) — este documento desarrolla
las sesiones **P4.1, P4.2, P4.3 y P5.1**.

**Plan anterior:**
[2026-09-20-prototipo-arenia-fase-p3-flujo-completo.md](2026-09-20-prototipo-arenia-fase-p3-flujo-completo.md)
— cerró la fase P3 y la **compuerta GP1** (1 586,61 USD y 7 de 7 por el camino de la pantalla).

## Situación de partida

- Rama `inc/PLAN-prototipo` en `f884044`, **sincronizada con `origin`**; PR #7 abierto con 41
  commits y la CI en verde en sus tres trabajos (calidad, ubuntu, windows).
- Meta del sprint **9/12**: faltan P10 (alguna prueba usa `AppTest`), P11 (cuarentena del corpus) y
  P12 (bitácora del sprint).
- `git diff p-base --stat -- core/` muestra **siete** archivos. **Este plan no añade ninguno.**

## Hechos verificados antes de escribir este plan (2026-09-21)

Se comprobaron con dos experimentos desechables contra el código de `f884044`. No son supuestos:

1. **`AppTest` abre la pantalla con `-W error`.** `AppTest.from_string("from ui.paginas.componer
   import render\nrender()\n", default_timeout=60)` corre sin excepción. La línea
   `missing ScriptRunContext!` que imprime Streamlit es un **registro de logging, no un aviso de
   Python**: no rompe `-W error` y no requiere `filterwarnings`.
2. **La base se desvía sin tocar código de producción.**
   `monkeypatch.setattr("ui.paginas.componer.RUTA_BASE_POR_DEFECTO", str(tmp_path / "x.db"))`
   **antes** del primer `at.run()` hace que el campo «Archivo SQLite» de la barra lateral nazca con
   esa ruta. Verificado por la fecha de modificación: `data/apu.db` queda intacta.
3. **Las tablas se siembran por `st.session_state`, y solo antes del primer `run()`.** La página
   inicializa `st.session_state[f"{clave}__filas"]` solo si no existe. Claves:
   `componer_materiales__filas`, `componer_equipos__filas`, `componer_mano_obra__filas`,
   `componer_cantidades__filas`. Cada fila es un `dict[str, str]` con las columnas de
   `COLUMNAS_MATERIALES`, `COLUMNAS_EQUIPOS`, `COLUMNAS_MANO_OBRA` y `COLUMNAS_CANTIDADES` del propio
   módulo. **Sembrar después de que la tabla ya se pintó no surte efecto** (el editor conserva su
   estado): se siembra todo antes del primer `run()`.
4. **Los widgets se localizan por su rótulo:** `"Codigo"`, `"Descripcion"`, `"Unidad"` y
   `componer.RENDIMIENTO_ETIQUETA` en `at.text_input`; las condiciones son `at.text_area[0]`; los
   botones `"Guardar composicion"` (con atributo `.disabled`) y `"Elaborar y auditar"`, que **solo
   existe cuando hay al menos una cantidad de obra válida**.
5. **Lo que se lee de vuelta:** la métrica `"Precio unitario"` vale `str(resultado.precio_unitario)`,
   sin redondear (p. ej. `"9.095350"`); tras elaborar, la métrica `"Total del presupuesto"` vale
   `f"{formatear_decimal(total, DECIMALES_PRESENTACION)} {moneda}"`; `at.get("download_button")`
   tiene un elemento.
6. **Una base vacía no permite guardar:** la página muestra el `st.error`
   `"no hay ninguna lista de precios vigente al <fecha>"`. Las pruebas que guardan siembran antes la
   base temporal con `scripts.seed_demo.main(["--db", str(base)])`.
7. **Con catálogo no vacío y una descripción tecleada, la ayuda 1 carga `sentence-transformers`**
   (se vio «Loading weights»). Las pruebas la sustituyen por un doble:
   `monkeypatch.setattr("ui.paginas.componer.sugerir_partidas_similares", lambda *_: [])`.
8. **Defecto real heredado de P3, reproducido:** `scripts/seed_demo.py` crea su lista de precios
   (fechada el 20/09/2026) **vacía**, sin heredar los precios de la vigente. Sembrar la línea base y
   después la demostración en la misma base deja las cinco partidas `LB-*` con
   `CatalogoIncompleto` desde el 20/09/2026 en adelante: la lista vigente pasa a ser la de la
   demostración y no tiene precio para ningún insumo de la clínica. La regla que se incumple ya
   está escrita en `core.catalog.precios.crear_lista_desde_archivo`: «la lista nueva nace con
   **todos** los precios de la anterior». `data/apu.db` todavía no está afectada: solo contiene la
   línea base. `scripts/seed_telecom.py`, `seed_industrial.py` y `seed_sistemas.py` repiten el mismo
   patrón (se declara en la bitácora; no se corrige en este plan).
9. **`MINIMO_OBSERVADO_PARA_ADVERTIR = 2`** (`core/catalog/rendimientos.py`). Ninguna partida
   sembrada tiene hoy dos observaciones de rendimiento, así que la advertencia RF‑27 **no puede
   dispararse en la aplicación sembrada**: el guion de prueba manual no tendría cómo ejercitarla.
10. **`buscar_referencia("", tipo)` devuelve todas las filas de ese tipo** (la cadena vacía es
    subcadena de cualquier descripción normalizada).
11. **`scripts/meta_prototipo.py::_referencias_ml_a_corpus` usa `ruta.relative_to(RAIZ)`**: con una
    carpeta `ml/` temporal fuera del repositorio lanza `ValueError`, así que la rama FALLA de P11 no
    tiene ni puede tener prueba tal como está.

## Global Constraints

- **`Decimal` en todo lo monetario y dimensional.** Nunca `float`. Se construye desde texto o desde
  enteros (`Decimal(generador.randint(1, 400)) / Decimal(100)`), jamás desde `random.random()`.
- **Ninguna tarea toca `core/`.** El recuento de `git diff p-base --stat -- core/` debe seguir en
  **siete** archivos al terminar. Si una tarea parece necesitar tocar `core/`, **para y reporta**.
- **`tests/unit/test_costing.py`, `tests/fixtures/apu_linea_base.py`,
  `tests/fixtures/presupuesto_auditado.py` y `tests/integration/test_auditoria_7_de_7.py` NO se
  modifican.**
- **Ninguna tarea cambia el esquema de la base** (`docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md`).
- **`ui/composicion.py` no importa `streamlit` ni `pandas`**, ni dentro de una función (meta P7).
- **Nunca se escribe en `data/apu.db`.** Las pruebas usan `tmp_path`; los scripts se corren con
  `--db` apuntando a un temporal. Toda prueba que abra un motor SQLAlchemy lo cierra con
  `motor.dispose()` (en Windows, un archivo abierto impide borrar el temporal).
- **Naturaleza de los datos (CLAUDE.md §1):** todo caso sembrado o simulado se declara didáctico o
  simulado en su docstring. `uv run --no-sync python scripts/meta_datos.py` debe seguir en **3/3**.
- ruff: `line-length = 100`, `target-version = "py312"`, reglas `E, F, W, I, B, UP, N`.
- **Idioma:** código, docstrings y documentación en español; **identificadores sin tildes**.
- **Commits:** Conventional Commits en español, **asunto sin tildes**.
- **Pruebas:** la CI corre `pytest -W error` con `--all-extras` y **falla si alguna prueba se
  omite**: nada de `skipif` ni `importorskip`.
- **Entorno:** el `.venv` ya está sincronizado; usa `uv run --no-sync`.
- **Los subagentes no empujan.** El push lo hace el controlador al cerrar P4 (compuerta GP2).

---

## Estructura de archivos

| Archivo | Responsabilidad | Tarea |
|---|---|---|
| `tests/unit/test_ui_componer.py` | **Nuevo.** Primeras pruebas `AppTest` de la pantalla | 1 |
| `docs/plan_pruebas.md` | Filas RF‑33 a RF‑35 en la matriz; enlace al guion | 1, 3 |
| `scripts/seed_demo.py` | Una sola orden: línea base + demostración valorables, presupuesto guardado, historial de rendimiento | 2 |
| `tests/integration/test_seed_demo.py` | **Nuevo.** Regresión del defecto 8 y lo que deja sembrado | 2 |
| `docs/guion_prueba_arenia.md` | **Nuevo.** Guion IEEE 829 de prueba manual, seis recorridos | 3 |
| `scripts/simular_corpus.py` | **Nuevo.** Corpus simulado determinista en su propia base | 4 |
| `tests/unit/test_simular_corpus.py` | **Nuevo.** Determinismo, validez y cuarentena del corpus | 4 |
| `scripts/meta_prototipo.py` | `_referencias_ml_a_corpus` relativa a su propia raíz | 4 |
| `tests/unit/test_meta_prototipo.py` | Las tres ramas de P11 | 4 |
| `ui/app.py` | Modo entrega: filtro puro de páginas | 5 |
| `tests/unit/test_ui_app.py` | **Nuevo.** El filtro, sin Streamlit | 5 |
| `docs/manual_usuario.md`, `docs/manual_tecnico.md` | Recorrido de composición; modalidad y contrato | 6 |
| `docs/bitacora/2026-09-16-sprint-prototipo.md` | **Nuevo.** Cierre del sprint (meta P12) | 6 |

**Orden de ejecución:** 1 → 2 → 3 → 4 → *(cierre de P4: push y CI, lo hace el controlador)* → 5 → 6.
La Tarea 1 siembra su base con `scripts.seed_demo.main`; la Tarea 2 cambia lo que ese `main` deja
sembrado y **debe dejar verde la Tarea 1**. La Tarea 3 describe la base que deja la Tarea 2. La
Tarea 6 cita la corrida de la CI del cierre de P4.

---

## Task 1: Las primeras pruebas de interfaz del repositorio (sesión P4.1, meta P10)

**Files:**
- Create: `tests/unit/test_ui_componer.py`
- Modify: `docs/plan_pruebas.md` (§8, matriz RF → prueba)

**Interfaces:**
- Consumes: `ui.paginas.componer` (`render`, `RUTA_BASE_POR_DEFECTO`, `RENDIMIENTO_ETIQUETA`,
  `sugerir_partidas_similares`); `scripts.seed_demo.main(argv) -> int`;
  `tests.fixtures.apu_linea_base.APU_TUBERIA` y `PARAMETROS_LINEA_BASE`;
  `core.costing.calcular_apu`; `core.catalog` (`Catalogo`, `abrir_sesion`, `crear_motor`);
  `core.verification.informe.DECIMALES_PRESENTACION`; `core.verification.texto.formatear_decimal`.
  Para convertir un `ComposicionAPU` en filas de tabla **no escribas otro conversor**:
  `tests/integration/test_composicion_extremo_a_extremo.py` ya tiene `_filas_materiales`,
  `_filas_equipos`, `_filas_mano_obra` y `_texto`. Impórtalos de allí: el repositorio ya importa
  ayudantes entre módulos de prueba (ese mismo archivo importa `_detectadas` de
  `tests/integration/test_auditoria_7_de_7.py`, y el commit `f884044` quitó la copia que había).
- Produces: nada que otra tarea consuma en código. La Tarea 3 se apoya en lo que estas pruebas
  demuestran.

**Lee primero** los «Hechos verificados» 1 a 7 de arriba: son el mapa de lo que `AppTest` puede y no
puede hacer con esta pantalla. Esta tarea **no debería necesitar tocar código de producción**. Si
alguna prueba revela un defecto real de la página, para y reporta antes de arreglarlo.

**El arnés común.** Una función del módulo que prepare la prueba, para no repetirla cinco veces:

```python
SCRIPT = "from ui.paginas.componer import render\nrender()\n"


def _pantalla(monkeypatch, base: Path, filas: dict[str, list[dict[str, str]]]) -> AppTest:
    """La pantalla contra `base`, con las tablas precargadas y la ayuda 1 sustituida por un doble."""
    monkeypatch.setattr("ui.paginas.componer.RUTA_BASE_POR_DEFECTO", str(base))
    monkeypatch.setattr("ui.paginas.componer.sugerir_partidas_similares", lambda *_: [])
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    for clave, valor in filas.items():
        at.session_state[clave] = valor
    at.run()
    return at
```

y un ayudante que teclee la cabecera de un `ComposicionAPU` (`codigo`, `descripcion`, `unidad` y
`_texto(apu.rendimiento)`) localizando cada campo por su rótulo.

**Las cinco pruebas.** Usa `APU_TUBERIA` del fixture (tiene materiales, equipos y mano de obra),
pero guárdalo con un código propio, `UI-01-TUB`, para que la prueba no dependa de si la base
sembrada ya trae las partidas `LB-*` (la Tarea 2 hará que las traiga):

1. `test_el_desglose_en_vivo_muestra_el_precio_unitario` — base vacía, tablas sembradas con las
   filas de `APU_TUBERIA`, cabecera tecleada: la métrica `"Precio unitario"` es exactamente
   `str(calcular_apu(<la composicion>, PARAMETROS_LINEA_BASE).precio_unitario)`, y además está a
   ±0,01 de `PRECIO_UNITARIO_ESPERADO["LB-02-TUB"]`. No hace falta guardar para verlo (UC‑10 paso 6).
2. `test_sin_condiciones_el_boton_de_guardar_esta_deshabilitado` — lo mismo, sin tocar el campo de
   condiciones: `"Guardar composicion"` tiene `disabled` verdadero. Al declarar condiciones pasa a
   falso (RF‑33).
3. `test_sin_rendimiento_guardar_no_persiste_nada` — base sembrada, condiciones declaradas,
   rendimiento en blanco: el botón está habilitado, pulsarlo muestra el `st.warning` de composición
   no válida, y al abrir la base **no existe** la partida `UI-01-TUB` (`Catalogo.partida` lanza
   `KeyError`). Esta es la mitad de RF‑33 que la prueba 2 no cubre: sin rendimiento declarado no se
   persiste nada.
4. `test_guardar_dos_veces_edita_la_partida` — base sembrada: guardar crea la partida (UC‑10);
   cambiar el rendimiento y volver a guardar la **edita** (UC‑11) en vez de fallar o duplicarla:
   `Catalogo(sesion).rendimientos("UI-01-TUB")` tiene dos registros con los dos valores tecleados.
5. `test_de_componer_a_excel_desde_la_pantalla` — base sembrada, tablas de insumos **y de
   cantidades** sembradas antes del primer `run()`
   (`[{"codigo_partida": "UI-01-TUB", "cantidad": "24", "origen_id": "prueba-ui"}]`): guardar, pulsar
   `"Elaborar y auditar"`, y comprobar que la métrica `"Total del presupuesto"` es
   `f"{formatear_decimal(Decimal('24') * pu, DECIMALES_PRESENTACION)} USD"` con `pu` calculado por
   `calcular_apu`, que hay exactamente un botón de descarga, y que ninguna prueba dejó excepción
   (`assert not at.exception`).

Todas las que guardan siembran antes su base temporal con
`assert seed_demo_main(["--db", str(base)]) == 0`. Todas comprueban `not at.exception` después de
cada `run()`. **Ninguna** lee ni escribe `data/apu.db`.

- [ ] **Step 1: Escribe las cinco pruebas y el arnés**

- [ ] **Step 2: Demuestra que no son vacuas**

Para cada prueba, rompe temporalmente **solo en memoria** la condición que vigila y comprueba que
falla por la razón esperada: por ejemplo, quita la fila de mano de obra de la siembra (el PU de la
prueba 1 debe dejar de coincidir), o no declares condiciones en la prueba 4 (no puede guardar).
Revierte cada cambio. No comitees nada de esto; anótalo en tu informe.

- [ ] **Step 3: Verde con las banderas de la CI**

```bash
uv run --no-sync pytest tests/unit/test_ui_componer.py -W error -p no:cacheprovider -v
```

Esperado: 5 pasan, 0 omitidas, sin avisos convertidos en error. **Si algún aviso de Streamlit sí
rompe `-W error`**, aplica la degradación del spec §8 en su primer escalón: una entrada acotada en
`filterwarnings` de `pyproject.toml`, **una por aviso, con un comentario que diga cuál es y por qué
se silencia**. Nada de silenciar categorías enteras.

- [ ] **Step 4: La matriz de pruebas**

En `docs/plan_pruebas.md` §8 añade las filas **RF‑33, RF‑34 y RF‑35** (lee su enunciado en
`docs/ERS.md`, sección de UC‑10 y UC‑11), cada una con las pruebas que la demuestran:
`tests/unit/test_ui_componer.py`, `tests/unit/test_composicion.py`,
`tests/integration/test_composicion_extremo_a_extremo.py` y, para el reemplazo,
`tests/integration/test_persistencia.py`. La columna «Casos» cuenta las funciones de prueba de cada
archivo: **cuéntalas, no las estimes** (`uv run --no-sync pytest <archivo> --collect-only -q`). No
reescribas el registro histórico de la ejecución del 14/09 (§10).

- [ ] **Step 5: Suite, lint y meta**

```bash
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
uv run --no-sync python scripts/meta_prototipo.py --hasta P4
```

Esperado: suite verde; ruff limpio; **P10 en OK** (P11 sigue PENDIENTE hasta la Tarea 4).

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_ui_componer.py docs/plan_pruebas.md
git commit -m "test(ui): primeras pruebas automatizadas de la interfaz con apptest"
```

---

## Task 2: Una sola orden deja la aplicación lista (sesión P4.2, primera mitad)

**Files:**
- Modify: `scripts/seed_demo.py`
- Create: `tests/integration/test_seed_demo.py`

**Interfaces:**
- Consumes: `scripts.seed.main(argv) -> int` y `scripts.seed.sembrar(sesion) -> models.Proyecto`
  (siembra la línea base con sus cinco rendimientos; **idempotente**: si el proyecto existe, no
  carga nada); `core.budget.guardar_presupuesto(session, presupuesto, informe, proyecto, lista,
  parametros)` y `core.budget.cargar_presupuesto(session, proyecto_nombre, codigo, catalogo)`;
  `core.catalog.rendimientos.registrar_rendimiento(session, codigo_partida, valor, tipo, fecha,
  condiciones)`, `dispersion_rendimientos`, `proponer_rendimiento`, `advertencia_rendimiento`;
  `core.contracts.TipoRendimiento`.
- Produces (la Tarea 3 los cita y la Tarea 1 debe seguir verde con ellos):
  - `elaborar_caso_demo(caso: CasoDemo) -> ResultadoElaboracion` — la elaboración del caso con
    `plan_secuencial`, **la única** del módulo: `_imprimir_resumen` pasa a usarla en vez de su copia
    en línea, y la usan también la persistencia y la prueba.
  - `FECHA_OBSERVACION_PREVIA: date` y `RENDIMIENTO_OBSERVACION_PREVIA: Decimal` — la segunda
    observación didáctica de `DEMO-01-INST`, anterior a `FECHA_DEMO`.
  - `main(["--db", ruta])` deja en la base: la línea base (5 partidas `LB-*`), la demostración
    (3 partidas `DEMO-*`), las dos listas, el presupuesto `DEMO-001` guardado con su informe, y dos
    observaciones de rendimiento para `DEMO-01-INST`. Todo idempotente.

**Por qué.** `PLAN_PROTOTIPO.md` P4.2 pide que un solo comando deje la aplicación lista de punta a
punta. Hoy hay dos defectos que lo impiden (hechos verificados 8 y 9): sembrar la línea base y la
demostración en la misma base **rompe la línea base**, y ninguna partida puede disparar la
advertencia de rendimiento que el guion manual tiene que ejercitar.

**Decisiones ya tomadas, con su coste si fueran equivocadas:**

- **La herencia de precios se corrige en `scripts/seed_demo.py`, no en `core/`.** La regla está en
  `crear_lista_desde_archivo`, pero esa función exige una lista anterior y lanza
  `CatalogoIncompleto` si no la hay, mientras que el sembrador debe funcionar también sobre una base
  vacía. Son semánticas distintas. El código cita la regla de `crear_lista_desde_archivo` en un
  comentario. *Coste si es equivocado:* cinco líneas que migrar a `core/catalog/precios.py` el día
  que un tercer creador de listas las necesite.
- **La lista de MaPreX no se importa al catálogo.** `PLAN_PROTOTIPO.md` P4.2 menciona «catálogo con
  insumos de la referencia MaPreX en USD», pero la pantalla ya ofrece esa referencia completa a
  través del buscador (`buscar_referencia`, P2.3), que lee los CSV directamente. Además,
  `crear_lista_desde_archivo` solo actualiza precios de insumos **ya catalogados**: con
  `lista_maprex_usd.csv` los 111 insumos saldrían como `desconocidos` y no se añadiría nada.
  *Coste si es equivocado:* ninguno para la pantalla; se declara en la bitácora de la Tarea 6.
- **La segunda observación de rendimiento va con fecha anterior a `FECHA_DEMO`**, para que
  `proponer_rendimiento` y `Catalogo.composicion` sigan devolviendo el rendimiento del caso: el
  total de la demostración y la prueba de extremo a extremo de P3 no se mueven.

**Las pruebas** (`tests/integration/test_seed_demo.py`), todas contra `tmp_path`:

1. `test_una_sola_orden_deja_linea_base_y_demo_valorables_hoy` — `main(["--db", base])`; a
   `date.today()`, cada `APU` de `tests.fixtures.apu_linea_base.APUS_LINEA_BASE` se reconstruye con
   `Catalogo.composicion(apu.codigo_partida)` y da **el mismo** `precio_unitario` que
   `calcular_apu(apu, PARAMETROS_LINEA_BASE)`; las tres `DEMO-*` se reconstruyen sin error.
   *Hoy falla:* `seed_demo` no siembra la línea base.
2. `test_sembrar_la_demo_sobre_una_base_con_linea_base_no_la_rompe` — primero
   `scripts.seed.main(["--db", base])`, después `seed_demo.main`; la misma aserción que la 1.
   *Hoy falla con `CatalogoIncompleto`:* es el escenario de quien ya tiene `data/apu.db` con la
   línea base y corre la demostración encima.
3. `test_deja_guardado_el_presupuesto_de_ejemplo` —
   `cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO_PRESUPUESTO, Catalogo(sesion)).total` es igual
   a `elaborar_caso_demo(construir_caso_demo()).presupuesto.total`. **No transcribas el total.**
4. `test_demo_01_tiene_historial_para_la_advertencia_de_rendimiento` — `dispersion_rendimientos`
   de `DEMO-01-INST` tiene al menos `MINIMO_OBSERVADO_PARA_ADVERTIR` observaciones;
   `advertencia_rendimiento(dispersion, dispersion.maximo * 2)` no es `None` y
   `advertencia_rendimiento(dispersion, dispersion.minimo)` sí lo es; `proponer_rendimiento` sigue
   proponiendo el rendimiento de la composición del caso.
5. `test_es_idempotente` — `main` dos veces sobre la misma base: los recuentos de `Partida`,
   `ListaPrecios`, `Presupuesto`, `PrecioInsumo` y `Rendimiento` no cambian.

- [ ] **Step 1: Escribe las cinco pruebas**

- [ ] **Step 2: Córrelas y verifica que 1, 2, 3 y 4 fallan por la razón anunciada**

```bash
uv run --no-sync pytest tests/integration/test_seed_demo.py -v
```

La 5 puede pasar ya: registra en tu informe cuál falla y con qué mensaje.

- [ ] **Step 3: Implementa**

En `scripts/seed_demo.py`:
- `sembrar_demo`: **antes** de crear su lista, resuelve la vigente a `caso.fecha` con
  `Catalogo(sesion).lista_vigente(caso.fecha)` (si no hay ninguna, `CatalogoIncompleto`: la base
  está vacía y no hay nada que heredar); después crea la lista nueva y copia a ella un
  `models.PrecioInsumo` por cada precio de la anterior, y solo entonces carga las composiciones.
  Tras cargarlas, registra la observación previa de `DEMO-01-INST` con `registrar_rendimiento`
  (`TipoRendimiento.ESTIMADO`, `FECHA_OBSERVACION_PREVIA`, `RENDIMIENTO_OBSERVACION_PREVIA` y unas
  condiciones que digan que es una **segunda estimación didáctica, no una ejecución medida**). El
  valor lo eliges tú, distinto del rendimiento del caso, y lo declaras como constante.
- `elaborar_caso_demo`: la elaboración que hoy vive en línea dentro de `_imprimir_resumen`, movida a
  una función propia, que `_imprimir_resumen` pasa a llamar.
- Una función `guardar_presupuesto_demo(sesion, proyecto, caso)` idempotente (no hace nada si el
  proyecto ya tiene un presupuesto con `caso.codigo_presupuesto`) que guarda
  `elaborar_caso_demo(caso)` con `guardar_presupuesto`, referenciando la lista vigente a
  `caso.fecha`.
- `main`: dentro de la sesión, `sembrar(sesion)` de `scripts.seed` (la línea base) → `sembrar_demo`
  → `guardar_presupuesto_demo` → commit → resumen. Actualiza el docstring del módulo (qué deja
  sembrado, y que ahora incluye la línea base) y su bloque «Uso».

- [ ] **Step 4: Verde, incluida la Tarea 1 y la prueba de extremo a extremo de P3**

```bash
uv run --no-sync pytest tests/integration/test_seed_demo.py tests/unit/test_ui_componer.py tests/integration/test_composicion_extremo_a_extremo.py -W error -v
```

- [ ] **Step 5: Córrelo de verdad, contra una base temporal**

```bash
TMP=$(uv run --no-sync python -c "import tempfile;print(tempfile.gettempdir())")
uv run --no-sync python scripts/seed_demo.py --db "$TMP/arenia_demo.db" --reiniciar
uv run --no-sync python scripts/seed_demo.py --db "$TMP/arenia_demo.db"
```

Reporta las dos salidas: la segunda debe ser idéntica a la primera (idempotencia). **Nunca contra
`data/apu.db`.**

- [ ] **Step 6: Suite, lint, metas**

```bash
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
uv run --no-sync python scripts/meta_datos.py
git diff p-base --stat -- core/
```

Esperado: verde; limpio; 3/3; **siete** archivos en `core/`, los mismos de antes.

- [ ] **Step 7: Commit**

```bash
git add scripts/seed_demo.py tests/integration/test_seed_demo.py
git commit -m "fix(scripts): la siembra de demostracion hereda precios y deja la base lista"
```

---

## Task 3: El guion de prueba manual de AREN.IA (sesión P4.2, segunda mitad)

**Files:**
- Create: `docs/guion_prueba_arenia.md`
- Modify: `docs/plan_pruebas.md` (un enlace al guion entre los entregables, §7)

**Interfaces:**
- Consumes: la base que deja `scripts/seed_demo.py` tras la Tarea 2; la pantalla
  `ui/paginas/componer.py`; `core/budget/excel.py` (los nombres de las cuatro hojas: constantes
  `HOJA_*`).
- Produces: el protocolo manual que se entrega a quien pruebe AREN.IA. La Tarea 6 lo enlaza desde
  el manual de usuario.

**Qué es.** Una especificación de casos de prueba al estilo **IEEE 829**, para una persona que no
programa. Encabezado: identificador, alcance, elementos a probar, entorno y preparación
(`uv sync --extra ui --extra ml`, `uv run python scripts/seed_demo.py --reiniciar`,
`uv run streamlit run ui/app.py`) y la declaración de que **los datos sembrados son didácticos, no
de obra ejecutada** (enlaza a `CLAUDE.md` §1, no la copies). Advierte que `--reiniciar` borra la
base: se usa sobre una base de prueba, nunca sobre una con trabajo propio.

**Seis casos, numerados `CP-01` a `CP-06`**, cada uno con precondición, pasos numerados, resultado
esperado **explícito**, y campos en blanco para el resultado obtenido y el veredicto:

| Caso | Recorrido | Qué debe observar quien prueba |
|---|---|---|
| CP‑01 | Componer una partida desde cero, con filas tomadas del buscador MaPreX | El PU del desglose en vivo, con su valor esperado |
| CP‑02 | Editar la partida de CP‑01 (UC‑11) | Mensaje de guardado; la partida no se duplica; el historial gana un rendimiento |
| CP‑03 | Una línea a destajo junto a otra a jornal | Cuánto sube el PU, y por qué no lleva FCAS ni bono (D9) |
| CP‑04 | Un rendimiento fuera de rango en `DEMO-01-INST` | La advertencia RF‑27, y que guardar sigue habilitado |
| CP‑05 | Exportar a Excel | Las cuatro hojas, por nombre; la columna *Modalidad* en la hoja APU |
| CP‑06 | Leer el informe de auditoría | Cuántos hallazgos y de qué severidad, para las cantidades del caso |

Cierra con una tabla de trazabilidad **CP → UC / RF**.

**Todo resultado esperado sale de ejecutar el sistema, no de la cabeza de quien escribe.** Para
cada caso reproduce el recorrido contra una base temporal sembrada con `seed_demo.py`, con
`AppTest` como en la Tarea 1 o con las funciones de `ui/composicion.py` y `core/`, y copia el valor
que sale. Los términos de búsqueda de CP‑01 deben devolver filas reales de
`buscar_referencia`: compruébalo. No comitees los guiones auxiliares que uses para calcularlos;
descríbelos en tu informe.

- [ ] **Step 1: Calcula y verifica los seis resultados esperados contra una base temporal**
- [ ] **Step 2: Escribe el guion**
- [ ] **Step 3: Enlázalo desde `docs/plan_pruebas.md` §7**
- [ ] **Step 4: Metas**

```bash
uv run --no-sync python scripts/meta_datos.py
uv run --no-sync python scripts/meta_prototipo.py --hasta P4
```

Esperado: 3/3 (el guion no puede presentar como real ningún dato didáctico).

- [ ] **Step 5: Commit**

```bash
git add docs/guion_prueba_arenia.md docs/plan_pruebas.md
git commit -m "docs(pruebas): guion de prueba manual de arenia"
```

---

## Task 4: Corpus simulado y su cuarentena (sesión P4.3, meta P11)

**Files:**
- Create: `scripts/simular_corpus.py`
- Create: `tests/unit/test_simular_corpus.py`
- Modify: `scripts/meta_prototipo.py` (solo `_referencias_ml_a_corpus`)
- Modify: `tests/unit/test_meta_prototipo.py`

**Interfaces:**
- Consumes: `ui.composicion` (`buscar_referencia`, `fila_materiales_desde_referencia`,
  `fila_equipos_desde_referencia`, `fila_mano_obra_desde_referencia`, `composicion_desde_tablas`);
  `core.catalog` (`Catalogo`, `abrir_sesion`, `crear_esquema`, `crear_motor`); `core.models`;
  `core.costing.calcular_apu`. El patrón de CLI y de semilla es el de `scripts/simular_lista.py`
  (`random.Random(semilla)`, `argparse`, el ajuste de `sys.path` a `RAIZ`): léelo y síguelo.
- Produces:
  - `generar_corpus(n: int, semilla: int) -> tuple[ComposicionAPU, ...]` — puro, sin base.
  - `sembrar_corpus(sesion: Session, composiciones: Sequence[ComposicionAPU], fecha: date) -> int`
    — crea una lista propia del corpus y carga cada composición; devuelve cuántas cargó.
  - `main(argv) -> int` con `--db` **obligatorio**, `--n` (200 por defecto) y `--semilla`
    (42 por defecto).

**Qué es y qué no es.** Un corpus de composiciones **simuladas** para probar la interfaz con
volumen: abrir la pantalla contra una base con cientos de partidas. **No** es un dato de mercado,
**no** proviene de obra ejecutada, **no** alimenta `ml/` y **no** cuenta para la compuerta G2, que
sigue cruzada con degradación a reglas. El docstring del módulo lo declara con esas palabras.

**La cuarentena tiene dos capas:**
1. **Por archivo:** `main` **se niega** (código de salida distinto de cero y mensaje en `stderr`) si
   el archivo de `--db` ya existe. El corpus vive siempre en su propia base, nunca mezclado con el
   catálogo de trabajo ni con `data/apu.db`. Como la base es nueva, `sembrar_corpus` no tiene lista
   anterior que heredar: el defecto 8 no puede reproducirse aquí.
2. **Por código:** la meta P11 falla si algún módulo de `ml/` menciona `simular_corpus`,
   `corpus_simulado` o «corpus simulado».

**Cómo se genera cada composición**, con un único `random.Random(semilla)`:
- código `f"SIM-{i:04d}"` desde 1, descripción que diga que es simulada, una unidad elegida de una
  tupla constante de unidades **que `normalizar_unidad` acepte** (compruébalo);
- entre 1 y 4 materiales, entre 0 y 2 equipos y entre 1 y 3 obreros, **sin repetir fila** dentro de
  una misma composición, tomados de `buscar_referencia("", tipo)` (hecho verificado 10). De los
  equipos, **solo los que traen `factor_depreciacion`**: sin él la fila no forma un `LineaEquipo`
  válido;
- cada fila rellenada con `fila_*_desde_referencia` y su cantidad puesta desde enteros
  (`Decimal(generador.randint(1, 400)) / Decimal(100)`); el rendimiento, también desde enteros;
- todo convertido con `composicion_desde_tablas`: el corpus ejercita la **misma** capa pura que usa
  la pantalla.

**Las pruebas** (`tests/unit/test_simular_corpus.py`):
1. Misma semilla → corpus idéntico; semilla distinta → corpus distinto.
2. `n` composiciones con códigos únicos.
3. **Ningún `float`**: todo campo numérico de cada línea y el rendimiento son `Decimal`.
4. Cada composición se calcula con `calcular_apu` y da un precio unitario mayor que cero.
5. `main` sobre un archivo que ya existe devuelve distinto de cero y **no** cambia el archivo.
6. `main(["--db", <nuevo>, "--n", "5"])` deja 5 partidas `SIM-*` que `Catalogo.composicion`
   reconstruye con el mismo precio unitario que la composición generada.
7. El docstring del módulo contiene «simulado» y declara que no cuenta para ninguna compuerta.

**La meta P11** (`tests/unit/test_meta_prototipo.py`): prueba sus tres ramas —
`evaluar_p11_ml_sin_corpus_simulado(None, ())` es PENDIENTE; con una referencia es FALLA; sin
referencias es OK— y que `_referencias_ml_a_corpus` detecta un módulo de una carpeta `ml/`
temporal que mencione `simular_corpus`. Esa última prueba **fallará** por el hecho verificado 11: la
corrección es calcular la ruta relativa respecto de `raiz_ml.parent`, no de `RAIZ`, sin cambiar lo
que la meta reporta sobre el repositorio real (`ml/<archivo>`).

- [ ] **Step 1: Escribe las pruebas del corpus y las de P11**
- [ ] **Step 2: Córrelas y verifica que fallan** (`ModuleNotFoundError` para el corpus; `ValueError`
  de `relative_to` para la de `_referencias_ml_a_corpus`)
- [ ] **Step 3: Implementa `scripts/simular_corpus.py` y la corrección de la meta**
- [ ] **Step 4: Verde**

```bash
uv run --no-sync pytest tests/unit/test_simular_corpus.py tests/unit/test_meta_prototipo.py -W error -v
```

- [ ] **Step 5: Córrelo de verdad, con volumen, contra un temporal**

```bash
TMP=$(uv run --no-sync python -c "import tempfile;print(tempfile.gettempdir())")
uv run --no-sync python scripts/simular_corpus.py --db "$TMP/corpus_simulado.db" --n 200
uv run --no-sync python scripts/simular_corpus.py --db "$TMP/corpus_simulado.db" --n 200
```

La primera carga 200; la segunda **se niega**. Reporta ambas salidas y el tiempo de la primera.

- [ ] **Step 6: Suite, lint, metas**

```bash
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
uv run --no-sync python scripts/meta_datos.py
uv run --no-sync python scripts/meta_prototipo.py --hasta P4
```

Esperado: verde; limpio; 3/3; **`--hasta P4` en 11/11** (P10 y P11 en OK).

- [ ] **Step 7: Commit**

```bash
git add scripts/simular_corpus.py tests/unit/test_simular_corpus.py scripts/meta_prototipo.py tests/unit/test_meta_prototipo.py
git commit -m "feat(scripts): corpus simulado para pruebas de volumen, en cuarentena"
```

---

## Cierre de la fase P4 (lo hace el controlador, no un subagente)

- `meta_prototipo.py --hasta P4` en **11/11**; suite verde con `-W error`; ruff limpio.
- `git push` de `inc/PLAN-prototipo` y espera de la CI del PR #7.
- **Compuerta GP2:** los tres trabajos de la CI en verde, **ubuntu y windows** incluidos. Se anota
  la URL de la corrida en el ledger para que la Tarea 6 la cite. Si Windows falla por algo propio
  de `AppTest`, se aplica la degradación del spec §8 (marcador y trabajo aparte, con la pérdida de
  cobertura declarada en `docs/plan_pruebas.md` y el guion manual absorbiéndola) y se decide **con
  esa evidencia**, no antes.

---

## Task 5: El modo entrega (sesión P5.1, primera parte)

**Files:**
- Modify: `ui/app.py`
- Create: `tests/unit/test_ui_app.py`

**Interfaces:**
- Consumes: las nueve funciones `render` que `ui/app.py` ya importa.
- Produces:

```python
@dataclass(frozen=True, slots=True)
class DefinicionPagina:
    render: Callable[[], None]
    titulo: str
    investigacion: bool  # True: pantalla de la tesis que AREN.IA no necesita


PAGINAS: tuple[DefinicionPagina, ...]  # las nueve, en el orden actual de main()
VARIABLE_MODO_ENTREGA = "ARENIA_MODO_ENTREGA"


def modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool: ...
def paginas_visibles(modo_entrega: bool) -> tuple[DefinicionPagina, ...]: ...
```

**Qué hace.** `PLAN_PROTOTIPO.md` P5.1: un modo opcional que muestra solo lo que AREN.IA necesita
—**actualización de precios, catálogo, componer, elaborar, histórico**— y oculta las pantallas de
investigación —**escenarios, similares, simulador, visor 3D**—. **Por defecto se ven las nueve.**
El modo se activa con la variable de entorno `ARENIA_MODO_ENTREGA=1` (exactamente `"1"`, sin
espacios alrededor; cualquier otro valor o su ausencia lo dejan apagado).

**La regla de `ui/app.py` que no se rompe:** el módulo no construye ningún objeto de Streamlit al
importarse (lo vigila `tests/unit/test_ui_importable.py`). `PAGINAS` es una tupla de
`DefinicionPagina`, que no es de Streamlit; los `st.Page` se siguen construyendo **solo dentro de
`main()`**, a partir de `paginas_visibles(modo_entrega_activo())`, con `default=True` en la
primera visible.

**Las pruebas** (`tests/unit/test_ui_app.py`), sin Streamlit:
1. Sin modo entrega, `paginas_visibles(False)` son las nueve, en el orden de hoy (compara títulos).
2. En modo entrega, exactamente las cinco de AREN.IA, en ese mismo orden relativo.
3. Ninguna de las cuatro de investigación aparece en modo entrega.
4. `modo_entrega_activo({"ARENIA_MODO_ENTREGA": "1"})` es verdadero; con `{}`, con `"0"` y con
   `"si"` es falso.

- [ ] **Step 1: Escribe las cuatro pruebas**
- [ ] **Step 2: Córrelas y verifica que fallan** (`ImportError` de `paginas_visibles`)
- [ ] **Step 3: Implementa** — y documenta en el docstring del módulo cómo se activa, en bash
  (`ARENIA_MODO_ENTREGA=1 uv run streamlit run ui/app.py`) y en PowerShell
  (`$env:ARENIA_MODO_ENTREGA = "1"; uv run streamlit run ui/app.py`).
- [ ] **Step 4: Verde, incluida la prueba de importación**

```bash
uv run --no-sync pytest tests/unit/test_ui_app.py tests/unit/test_ui_importable.py -W error -v
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
```

- [ ] **Step 5: Commit**

```bash
git add ui/app.py tests/unit/test_ui_app.py
git commit -m "feat(ui): modo entrega que oculta las pantallas de investigacion"
```

---

## Task 6: Manuales, bitácora y cierre del sprint (sesión P5.1, segunda parte, meta P12)

**Files:**
- Modify: `docs/manual_usuario.md`
- Modify: `docs/manual_tecnico.md`
- Create: `docs/bitacora/2026-09-16-sprint-prototipo.md`
- Verify (regenerar y comprobar que no cambian): `docs/api.json`, `docs/resultados_ml.md`

**Interfaces:**
- Consumes: todo lo anterior; los cuatro ledgers de `.superpowers/sdd/` del sprint
  (`2026-09-16-prototipo-arenia-fase-p0-p1`, `2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion`,
  `2026-09-20-prototipo-arenia-fase-p3-flujo-completo`, y el de este plan), que **no viajan con la
  fusión** porque están en `.git/info/exclude`: lo que importe de ellos tiene que quedar en la
  bitácora; las bitácoras de sesión ya escritas en `docs/bitacora/` (`2026-09-16-P0-hallazgo-destajo.md`,
  `2026-09-20-P2-deudas-y-composicion.md`, `2026-09-20-P2-hallazgo-migraciones.md`), que se
  **enlazan**, no se copian; el formato de cierre de `docs/bitacora/2026-09-02-sprint-multidominio.md`.
- Produces: la meta **P12**, que busca en `docs/bitacora/` un archivo cuyo nombre contenga
  «prototipo».

**Manual de usuario.** El recorrido de composición tal como lo vive quien presupuesta: cabecera,
las tres tablas y el buscador MaPreX, rendimiento **con sus condiciones** (por qué es obligatorio),
el desglose en vivo, las cuatro ayudas (que sugieren y nunca bloquean), guardar y editar, cantidades
de obra con su origen, elaborar, el informe de auditoría y la descarga en Excel. Además: cómo dejar
la aplicación lista (`scripts/seed_demo.py`), el modo entrega, y un enlace al guion
`docs/guion_prueba_arenia.md`.

**Manual técnico.** La modalidad de mano de obra (D9): el campo `LineaManoObra.modalidad`, la
fórmula del destajo en el motor, y por qué la hipótesis central no se ve afectada; los contratos y
funciones nuevos del sprint (`ModalidadManoObra`, `Catalogo.reemplazar_composicion`, la capa pura
`ui/composicion.py`); cómo se prueba la interfaz con `AppTest` (siembra por `st.session_state`,
desvío de `RUTA_BASE_POR_DEFECTO`, el doble de la ayuda 1); el corpus simulado y su cuarentena; y
la regla de las migraciones. Enlaza a la ERS, al spec y a la arquitectura; no los copies.

**La bitácora de cierre del sprint** (`docs/bitacora/2026-09-16-sprint-prototipo.md`), con el
formato de la del sprint multidominio:
- **Las tres compuertas con su evidencia:** GP0 (D9 y D4 en el dossier), GP1 (1 586,61 USD y 7 de 7,
  commit `1558587`), GP2 (la corrida de la CI del cierre de P4, con su URL, que está en el ledger).
- **El cambio al núcleo y su expediente:** los siete archivos de `git diff p-base --stat -- core/`,
  qué cambió en cada uno y por qué ninguno rompe la hipótesis central.
- **Los hallazgos del sprint:** el destajo del art. 114 de la LOTTT (D9); el FCAS sin fuente
  normativa (D4); la ausencia de herramienta de migraciones; que `AppTest` no conduce
  `st.data_editor` y cómo se resolvió; el defecto de la lista sin herencia (hecho verificado 8), su
  corrección en `seed_demo` y **el mismo patrón latente en los sembradores telecom, industrial y
  sistemas**, sin corregir y con la corrección de cinco líneas descrita; la lista de MaPreX que no se
  importó al catálogo y por qué (Tarea 2).
- **Métricas finales:** número de pruebas de la suite, 0 omitidas, meta 12/12.
- **Pendiente del tutor:** D9, D4 y lo que los ledgers marquen como abierto.

**Nada de la bitácora ni de los manuales presenta como real un dato didáctico.**

- [ ] **Step 1: Lee los cuatro ledgers y las tres bitácoras de sesión**
- [ ] **Step 2: Escribe los dos manuales**
- [ ] **Step 3: Escribe la bitácora**
- [ ] **Step 4: Artefactos reproducibles**

```bash
uv run --no-sync python scripts/exportar_openapi.py
uv run --no-sync python scripts/generar_resultados_ml.py
git diff --exit-code -- docs/api.json docs/resultados_ml.md
```

Esperado: sin diferencias (este sprint no cambia la API ni `ml/`). Si hay diferencias, para y
reporta: significaría que algo de este sprint tocó lo que no debía.

- [ ] **Step 5: Cierre**

```bash
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
uv run --no-sync python scripts/guardia_nucleo.py --base p-base
uv run --no-sync python scripts/meta_datos.py
uv run --no-sync python scripts/meta_prototipo.py
```

Esperado: verde; limpio; guardia OK; 3/3; **12/12**.

- [ ] **Step 6: Commit**

```bash
git add docs/manual_usuario.md docs/manual_tecnico.md docs/bitacora/2026-09-16-sprint-prototipo.md
git commit -m "docs: cierre del sprint del prototipo arenia"
```

---

## Cierre del sprint

- `meta_prototipo.py` en **12/12**; las tres compuertas cruzadas y anotadas en la bitácora.
- `git diff p-base --stat -- core/` en **siete** archivos, los mismos que al abrir este plan.
- La rama se empuja y el PR #7 se actualiza para describir las fases P0 a P5.
- **La auditoría de la rama completa se pauta con Eugenio antes de fusionar**; no se lanza por
  iniciativa propia (las revisiones de este repositorio se agrupan en auditorías, no por tarea).
