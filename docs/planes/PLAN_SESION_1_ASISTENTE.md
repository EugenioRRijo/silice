# Sesión 1 — Asistente de IA: cerrar sus deudas (Sílice 1.1.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar lo que el asistente de IA dejó abierto en la 1.0.0: la advertencia de variaciones de precio
atípicas (RF-100), la reactivación de la clave de IA desde su respaldo cifrado, las siete pruebas del experimento
que faltan y el informe de resultados que se puede generar sin gastar.

**Architecture:** Todo fuera de `core/`. RF-100 = una función pura nueva en `ml/anomaly/serie.py` (sin base de
datos) + el armado de la serie desde la base en `ui/composicion.py` + su muestra en la pestaña Precios de la hoja y
en la página de la lista de la empresa. La reactivación reutiliza `ClaveDeIA.activar(empresa_id, contrasena)`, que ya
existe; falta la función de administración y la pantalla. Las pruebas del experimento siguen lo que ya especifica
`PLAN_SILICE_090.md` (Tareas 17–19).

**Tech Stack:** Python 3.12, `uv`, pytest (`-W error`), Streamlit `AppTest`, scikit-learn (extra `ml`), keyring
(extra `ia`).

**Spec:** `docs/especificaciones/2026-10-11-silice-s3-auditor-paquete-design.md` (RF-100, §3.2 y §4) y
`docs/especificaciones/2026-10-11-silice-s4-asistente-ia-design.md` (§8.3 clave de IA, §9 experimento, RF-95).
Orden y subagentes: [RUTA_SESIONES.md](./RUTA_SESIONES.md) §5, sesión 1.

## Global Constraints

- `git diff origin/main -- core/` vacío; `uv run python scripts/guardia_nucleo.py --base origin/main` en OK.
- `ml/` no importa la base de datos ni `sqlalchemy` (`tests/unit/test_arquitectura*.py`).
- RF-100: severidad **ADVERTENCIA**, código `CODIGO_ATIPICO` (`"ATIPICO"`, `core/budget/presupuesto.py:57`), **nunca
  ERROR**; no bloquea guardar, exportar ni firmar; sin el extra `ml` no hay hallazgo ni traza.
- Detector sin cambios: `SEMILLA = 42`, `UMBRAL_ATIPICO = -0.05`, `MINIMO_OBSERVACIONES = 8`
  (`ml/anomaly/detector.py`).
- RF-100 corre en la pestaña Precios y en la lista de la empresa; **no** en la reauditoría del paquete ni en la API.
- RNF-18: ni la clave de IA ni la contraseña del respaldo quedan en `st.session_state`, en registros ni en mensajes.
- Ninguna prueba abre la red; ninguna llama a la API de pago.
- Montos en `Decimal`; TDD con rojo visto (commit de la prueba en rojo antes que el de la implementación).
- Commits convencionales en español, asunto sin tildes.

## Review Focus

1. **Serie con precios en Bs sin tasa** → el punto no se puede llevar a USD: se omite de la serie (no se inventa
   una tasa) y la prueba fija que la serie resultante no lo incluye.
2. **Dos listas con la misma fecha para el mismo insumo** → orden estable por (fecha, id de lista); la prueba fija
   el orden y los ids de las variaciones.
3. **Precio anterior igual a cero** → esa variación no se calcula (división por cero); la prueba fija que no
   aparece y que no lanza excepción.
4. **Contraseña del respaldo incorrecta** → mensaje fijo, sin la contraseña ni la clave, y la clave sigue sin
   cargarse; la prueba busca la contraseña en `st.session_state` y en los mensajes tras el intento.
5. **Reactivar desde otro equipo o sin ser administrador** → rechazo con el mismo mensaje que al registrar la clave.

---

### Task 1.1: RF-100, variaciones atípicas en la serie de precios de un insumo

**Subagente:** `silice-asistente-ia` · **Modelo:** Sonnet · **Esfuerzo:** high

**Files:**
- Create: `ml/anomaly/serie.py`
- Modify: `ml/anomaly/__init__.py` (exportar `PrecioFechado`, `variaciones_de_serie`, `variaciones_atipicas`)
- Modify: `ui/composicion.py` (agregar `serie_usd_de_insumo` y `atipicos_de_insumo`)
- Modify: `ui/paginas/hoja.py` (`_pestana_precios`, línea ~1864) y `ui/paginas/precios_empresa.py` (mostrar las
  advertencias)
- Test: `tests/unit/test_ml_serie_precios.py`, `tests/unit/test_composicion_atipicos.py`

**Interfaces:**
- Consumes: `ml.anomaly.precios_atipicos(variaciones: Mapping[str, Decimal]) -> list[PrecioAtipico]`
  (`PrecioAtipico(id: str, valor: Decimal, puntaje: float)`); modelos `ListaPrecios(moneda, fecha_vigencia)`,
  `PrecioInsumo(lista_id, insumo_id, precio)`, `ListaPreciosOrigen(lista_id, tasa, fecha_tasa)`;
  `core.contracts.verificacion.Hallazgo`, `Severidad.ADVERTENCIA`; `CODIGO_ATIPICO`.
- Produces:
  - `@dataclass(frozen=True, slots=True) class PrecioFechado: fecha: date; precio_usd: Decimal; origen: str`
    (`origen` = `"lista:<id>"`).
  - `variaciones_de_serie(serie: Sequence[PrecioFechado]) -> dict[str, Decimal]`: ordena por `(fecha, origen)`;
    variación `(p_i − p_{i−1}) / p_{i−1}`; id = `f"{fecha_i.isoformat()}|{origen_i}"`; omite el par si
    `p_{i−1} == 0`.
  - `variaciones_atipicas(serie: Sequence[PrecioFechado]) -> list[PrecioAtipico]` =
    `precios_atipicos(variaciones_de_serie(serie))`.
  - `serie_usd_de_insumo(session: Session, insumo_id: int) -> list[PrecioFechado]`: un punto por `PrecioInsumo` de
    ese insumo en **todas** las listas; USD tal cual; Bs ÷ `ListaPreciosOrigen.tasa` de su lista; Bs sin tasa se
    omite.
  - `atipicos_de_insumo(session: Session, insumo_id: int, cargar_anomalia: Callable[[], ModuleType] =
    _importar_anomalia) -> list[Hallazgo]`: un `Hallazgo(regla=CODIGO_ATIPICO, severidad=Severidad.ADVERTENCIA,
    descripcion=…, valor_observado=<variación>, origen_ids=(<id>,))` por variación atípica; `[]` si `ml` no está
    o falla (mismo patrón que `advertencia_precio_atipico`, `ui/composicion.py:640`).

- [ ] **Step 1: Write the failing tests** (`tests/unit/test_ml_serie_precios.py`)

```python
# Serie sembrada: diez precios mensuales en USD; un salto entre el 5.o y el 6.o punto.
# Variaciones a mano: 10.00→10.10 = 0.01; 10.10→10.20 ≈ 0.0099; …; 10.40→20.00 ≈ 0.923 (la sembrada); …
SEMBRADA = [10.00, 10.10, 10.20, 10.30, 10.40, 20.00, 20.20, 20.40, 20.60, 20.80]
SIN_ATIPICO = [10.00, 10.10, 10.20, 10.30, 10.40, 10.50, 10.60, 10.70, 10.80, 10.90]

def test_un_atipico_sembrado_da_exactamente_ese_punto():
    marcas = variaciones_atipicas(_serie(SEMBRADA))
    assert [m.id for m in marcas] == ["2026-06-01|lista:6"]

def test_sin_atipico_conjunto_vacio():
    assert variaciones_atipicas(_serie(SIN_ATIPICO)) == []

def test_ocho_precios_siete_variaciones_se_abstiene():
    assert variaciones_atipicas(_serie(SEMBRADA[:8])) == []

def test_precio_anterior_cero_no_lanza_y_omite_la_variacion():
    v = variaciones_de_serie(_serie([0, 10, 11]))
    assert list(v) == ["2026-03-01|lista:3"] and v["2026-03-01|lista:3"] == Decimal("0.1")

def test_misma_fecha_orden_estable_por_origen():
    ...  # dos puntos con fecha 2026-01-01 y origen lista:2 y lista:1 → lista:1 primero
```

`_serie(valores)` arma `PrecioFechado(date(2026, i, 1), Decimal(str(v)), f"lista:{i}")` con `i` desde 1. Si el
bosque no marca el punto sembrado con estos valores, **se agranda el salto** (el oráculo es *cuál* punto se sembró,
no el umbral) y se anota el valor usado en el comentario de la prueba; los umbrales del detector no se tocan.

- [ ] **Step 2: Run to verify it fails** — `uv run pytest tests/unit/test_ml_serie_precios.py -W error -v` →
  FAIL (`ModuleNotFoundError: ml.anomaly.serie`).
- [ ] **Step 3: Implement `ml/anomaly/serie.py`** con las firmas de *Produces*; sin importar `sqlalchemy`.
- [ ] **Step 4: Run to verify it passes** — mismo comando → PASS.
- [ ] **Step 5: Write the failing tests** (`tests/unit/test_composicion_atipicos.py`) con una base SQLite en
  `tmp_path` (patrón de `tests/unit/test_composicion*.py`):
  - `test_bs_se_lleva_a_usd_con_la_tasa_de_su_lista`: precio 1010 Bs con tasa 100 → `precio_usd == Decimal("10.10")`.
  - `test_bs_sin_tasa_se_omite`: el punto no aparece en la serie.
  - `test_atipico_es_advertencia_con_codigo_atipico`: la serie SEMBRADA en listas → un solo `Hallazgo`, `regla ==
    "ATIPICO"`, `severidad is Severidad.ADVERTENCIA`.
  - `test_sin_extra_ml_no_hay_hallazgo`: `cargar_anomalia` que lanza `ImportError` → `[]`.
- [ ] **Step 6: Run → FAIL; implement in `ui/composicion.py`; run → PASS.**
- [ ] **Step 7: Mostrar en la pestaña Precios y en la lista de la empresa**: una advertencia por insumo con
  hallazgos (`st.warning`, texto con `texto_seguro`), rotulada «[ML] variación atípica». Prueba `AppTest` en el
  archivo de pruebas existente de la página (`tests/unit/test_ui_hoja*.py` o `test_ui_precios_empresa*.py`): con la
  serie sembrada aparece una advertencia; sin ella, ninguna.
- [ ] **Step 8: Commit** — `feat(ml): advertencia de variaciones de precio atipicas en la serie del insumo (RF-100)`.

### Task 1.2: reactivar la clave de IA desde el respaldo cifrado

**Subagente:** `silice-asistente-ia` · **Modelo:** Opus · **Esfuerzo:** high

**Files:**
- Modify: `asistente/clave.py` (método `pide_contrasena`)
- Modify: `asistente/administracion.py` (función `reactivar_clave`)
- Modify: `ui/paginas/administracion.py` (sección y callback `_reactivar_clave`, junto a `_registrar_clave`)
- Test: `tests/unit/test_asistente_clave.py`, `tests/unit/test_asistente_administracion.py`,
  `tests/unit/test_ui_administracion_asistente.py` (archivos existentes)

**Interfaces:**
- Consumes: `ClaveDeIA.activar(empresa_id: str, contrasena_respaldo: str | None = None) -> None`
  (`asistente/clave.py:172`); `cliente.operacion_sensible_permitida()`; `_exigir(es_administrador)`;
  `CLAVES_DEL_FORMULARIO` (`ui/paginas/administracion.py:451`).
- Produces:
  - `ClaveDeIA.pide_contrasena(self, empresa_id: str) -> bool`: `True` si no hay clave en memoria, el almacén no
    la tiene (un error de almacén cuenta como «no la tiene») y existe el respaldo cifrado.
  - `reactivar_clave(clave: ClaveDeIA, empresa_id: str, contrasena: str, *, es_administrador: bool, ip_cliente: str
    | None) -> None`: exige administrador; exige bucle local (misma regla que `registrar`); llama `activar`; toda
    falla de descifrado se convierte en `ClaveNoRegistrable("La contraseña no abre el respaldo de la clave de IA.")`.
  - Clave de estado de la pantalla `"ia_contrasena_reactivar"`, agregada a `CLAVES_DEL_FORMULARIO`.

- [ ] **Step 1: Write the failing tests**
  - `test_pide_contrasena_solo_con_respaldo_y_sin_almacen` (almacén en memoria vacío + archivo de respaldo).
  - `test_reactivar_con_la_contrasena_correcta_carga_la_clave` (`clave.vigente == <clave de prueba>`).
  - `test_reactivar_con_contrasena_incorrecta_mensaje_fijo_y_sin_clave` (el mensaje no contiene la contraseña).
  - `test_reactivar_sin_ser_administrador_sin_permiso` y `test_reactivar_desde_otro_equipo_se_rechaza`.
  - AppTest: `test_la_contrasena_de_reactivar_no_queda_en_la_pantalla` (tras pulsar, `st.session_state
    ["ia_contrasena_reactivar"] == ""` y ningún valor del estado contiene la contraseña ni la clave).
  - AppTest: `test_la_seccion_solo_aparece_si_pide_contrasena`.
- [ ] **Step 2: Run → FAIL** — `uv run pytest tests/unit/test_asistente_clave.py
  tests/unit/test_asistente_administracion.py tests/unit/test_ui_administracion_asistente.py -W error`.
- [ ] **Step 3: Implement** las firmas de *Produces*; la sección muestra un `text_input(type="password")` y un
  botón «Reactivar la clave»; mensajes con `_avisar`/`texto_seguro`/`enmascarar` como `_registrar_clave`.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5:** Cerrar el hueco en la bitácora 0.9.0: anotar en `docs/bitacora/2026-10-ruta-s1.md` que el hueco
  de T15 (`docs/bitacora/2026-10-silice-090.md:138-141`) queda resuelto, con el commit.
- [ ] **Step 6: Commit** — `feat(asistente): reactivar la clave de IA desde el respaldo cifrado`.

### Task 1.3: las siete pruebas del experimento que faltan

**Subagente:** `silice-pruebas` · **Modelo:** Sonnet · **Esfuerzo:** high

**Files (Create):** `tests/fixtures/asistente_corridas.py`, `tests/unit/test_experimento_comparador.py`,
`tests/unit/test_experimento_metricas.py`, `tests/unit/test_experimento_mutaciones.py`,
`tests/unit/test_experimento_ejecucion.py`, `tests/unit/test_experimento_congelado.py`,
`tests/unit/test_evaluar_asistente.py`

**Interfaces:**
- Consumes: `asistente/experimento/{comparador,metricas,mutaciones,ejecucion,congelado}.py`,
  `scripts/evaluar_asistente.py` (`main(argv)`, órdenes `informe`, `mutaciones`, `repuntuar`, `corrida`).
- Produces: las pruebas que `PLAN_SILICE_090.md` especifica en **Tarea 17** (comparador E1–E8, línea 11179),
  **Tarea 18** (métricas, mutaciones, corrida y congelado, línea 12077) y **Tarea 19** (`evaluar_asistente.py` y la
  medición controlada, línea 13322).

- [ ] **Step 1:** Leer las tres tareas del plan 0.9.0 y escribir cada prueba **como está especificada** (sus valores
  esperados son los oráculos escritos a mano entonces).
- [ ] **Step 2: Run** — `uv run pytest <los siete archivos> -W error -v`. Esta vez el código ya existe: una prueba
  que falla **no se ajusta al código**; se decide si es defecto del código (se informa al orquestador con la
  evidencia y se corrige en esta tarea con su commit `fix(...)`) o error del plan 0.9.0 (ruling registrado, con la
  cuenta corregida a mano).
- [ ] **Step 3:** Mutación por prueba (rev-pruebas): para cada archivo, anotar en el informe una mutación del
  código que la prueba atrapa.
- [ ] **Step 4: Commit** — `test(experimento): pruebas del comparador, metricas, mutaciones, corrida y congelado`.

### Task 1.4: informe del experimento sin gasto (RF-95, parcial)

**Subagente:** `silice-asistente-ia` · **Modelo:** Sonnet · **Esfuerzo:** medium

**Files:**
- Create: `docs/resultados_asistente.md` (generado, **nunca editado a mano**)
- Modify (si hace falta): `asistente/experimento/protocolo.json` y `asistente/experimento/congelado.json`
- Test: `tests/unit/test_evaluar_asistente.py` (de la Tarea 1.3)

- [ ] **Step 1: Verificar el protocolo.** `uv run python -c "from asistente.experimento import congelado;
  print(congelado.verificar())"` → `[]`. `protocolo.json` declara `"modelo_local": "muse-glimmer"`: comprobar que
  existe en la biblioteca de Ollama **con uso de herramientas**; si no, ruling: elegir uno que sí (anotar nombre,
  tamaño y fuente), cambiar el protocolo y volver a congelar con `congelado.congelar(<commit>)`.
- [ ] **Step 2: Generar** con lo que no gasta: medición controlada de mutaciones del auditor
  (`uv run python scripts/evaluar_asistente.py mutaciones …`) y `informe`. Las secciones de las corridas con Claude y
  con Ollama quedan **PENDIENTE** con su bloqueo (B-1, B-2 de la ruta §6), escritas por el script, no a mano.
- [ ] **Step 3:** `uv run python scripts/meta_silice.py --version 0.9.0 --hasta S4-4` y anotar en la bitácora qué
  queda en OK y qué en PENDIENTE (con su bloqueo).
- [ ] **Step 4: Commit** — `docs(experimento): resultados de la medicion controlada (RF-95 parcial)`.

### Task 1.5: cierre de la 1.1.0

**Subagente:** `silice-escriba` · **Modelo:** Haiku · **Esfuerzo:** low (el orquestador corre la compuerta)

- [ ] **Step 1:** `pyproject.toml` → `version = "1.1.0"`; `uv lock`; `uv run python scripts/verificar_version.py`.
- [ ] **Step 2:** `CHANGELOG.md`: sección `1.1.0` con RF-100, reactivación de la clave, pruebas del experimento e
  informe parcial (texto que dicta el orquestador).
- [ ] **Step 3:** Bitácora `docs/bitacora/2026-10-ruta-s1.md` con rulings, resultados y bloqueos (al dictado).
- [ ] **Step 4 (orquestador):** compuerta de la ruta §4 paso 5 (suite completa, ruff, guardia, revisores
  arquitectura, seguridad, requisitos, pruebas y hechos), PR, CI verde, fusión, etiqueta `v1.1.0`.
