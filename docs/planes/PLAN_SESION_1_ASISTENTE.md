# Sesión 1 — Asistente de IA: cerrar sus deudas (Sílice 1.1.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar lo que el asistente de IA dejó abierto en la 1.0.0: la advertencia de variaciones de precio
atípicas (RF-100), la reactivación de la clave de IA desde su respaldo cifrado, las pruebas del experimento que
faltan, el informe de resultados que se puede generar sin gastar y la enmienda de la ERS.

**Architecture:** Todo fuera de `core/`. RF-100 se construye **exactamente como lo especifica la Tarea 22 de
`PLAN_SILICE_080.md`** (líneas 20265–20816): función pura en `ml/anomaly/series.py` (sin base), lectura de la base en
`ui/atipicos.py` (nuevo, sin Streamlit ni pandas) y el botón en la pestaña Precios. La reactivación reutiliza
`ClaveDeIA.activar(empresa_id, contrasena)`, que ya descifra el respaldo; falta un método que aplique la regla del
bucle local, la función de administración y la pantalla. Las pruebas del experimento siguen las Tareas 17–19 de
`PLAN_SILICE_090.md`.

**Tech Stack:** Python ≥ 3.12 (`pyproject.toml`), `uv` (con todos los extras: `uv sync --all-extras --frozen`), pytest (`-W error`),
Streamlit `AppTest`, scikit-learn (extra `ml`), keyring (extra `ia`).

**Spec:** `docs/especificaciones/2026-10-11-silice-s3-auditor-paquete-design.md` (RF-100: §3.2 y §14, fase S3-6) y
`docs/especificaciones/2026-10-11-silice-s4-asistente-ia-design.md` (§8.3 clave de IA, §9 experimento, RF-95).
Oráculo de RF-100: `tests/fixtures/memorias/atipicos_s3.md` (a mano, ya versionado). Orden y subagentes:
[RUTA_SESIONES.md](./RUTA_SESIONES.md) §5, sesión 1.

## Global Constraints

- `git diff origin/main -- core/` vacío; `uv run python scripts/guardia_nucleo.py --base origin/main` en OK.
- `ml/` no importa la base de datos ni `sqlalchemy`; `ui/composicion.py` tampoco (RA-2,
  `tests/unit/test_arquitectura.py:221-228`): **la lectura de la base de RF-100 va en `ui/atipicos.py`**.
- Nombres que exige la meta (`scripts/meta_silice_s3.py:86-87`): `ml/anomaly/series.py` ↔
  `tests/unit/test_series_atipicas.py` y `ui/atipicos.py` ↔ `tests/integration/test_atipicos.py`.
- RF-100: severidad **ADVERTENCIA**, código `CODIGO_ATIPICO` (`"ATIPICO"`, `core/budget/presupuesto.py:57`), **nunca
  ERROR**; no bloquea guardar, exportar ni firmar; sin el extra `ml` devuelve `None`, sin hallazgo ni traza; las
  listas de alcance `proyecto` no entran; un precio en Bs sin tasa se omite **y se nombra** (`sin_tasa`).
- Detector sin cambios: `SEMILLA = 42`, `UMBRAL_ATIPICO = -0.05`, `MINIMO_OBSERVACIONES = 8`. Los valores de prueba
  son los de la memoria; **no se ajustan series al detector**.
- RF-100 corre en la pestaña Precios (y al revisar la lista de la empresa); **no** en la reauditoría del paquete ni
  en la API.
- RNF-18 y RV-15: ni la clave de IA ni la contraseña del respaldo quedan en `st.session_state`, en registros ni en
  mensajes; registrar **y reactivar** la clave solo desde el propio equipo.
- Ninguna prueba abre la red; ninguna llama a la API de pago. TDD con rojo visto; `Decimal` para montos.
- Commits convencionales en español, asunto sin tildes.

## Review Focus

1. **Dos listas con la misma fecha** → orden por fecha y, a igual fecha, por **nombre de la lista** (memoria §5); la
   prueba de ordenamiento de la Tarea 22 lo fija.
2. **El origen del precio contradice a la lista** (moneda o tasa distintas en `PrecioOrigen`) → manda el precio
   (`test_el_origen_del_precio_manda_sobre_la_lista`).
3. **Contraseña del respaldo incorrecta o respaldo dañado** → mensaje fijo, sin la contraseña ni la clave, y la
   clave sigue sin cargarse; la contraseña **vacía** conserva su mensaje propio («Escriba la contraseña…»).
4. **Reactivar desde otro equipo** → rechazo, y la sección ni se muestra si `cliente.operacion_sensible_permitida()`
   lo niega.
5. **Hoja con una versión en solo lectura** → el botón de atípicos solo lee; no guarda nada.

---

### Task 1.1: RF-100, la serie fechada de un insumo en USD y su advertencia

**Subagente:** `silice-asistente-ia` · **Modelo:** Sonnet (excepción RS-7) · **Esfuerzo:** high

**Files:** los de la Tarea 22 de `PLAN_SILICE_080.md`:
- Create: `ml/anomaly/series.py`, `ui/atipicos.py`
- Modify: `ui/paginas/hoja.py` (pestaña Precios, `_pestana_precios` en la línea ~1864 hoy; las líneas que cita la
  Tarea 22 se movieron), `tests/unit/test_arquitectura.py` (`PROHIBIDOS_EN_UI["ui/atipicos.py"] = ("streamlit",
  "pandas")`)
- Test: `tests/unit/test_series_atipicas.py`, `tests/integration/test_atipicos.py`, `tests/unit/test_ui_hoja_atipicos.py`

**Interfaces:** las de la Tarea 22 (`PuntoDePrecio`, `SerieEnUsd`, `ResultadoDeSerie`, `a_usd`, `variaciones`,
`analizar`; `puntos_del_insumo`, `hallazgos_de_la_serie`, `atipicos_del_insumo`). Para la moneda y la tasa de cada
precio, **reutilizar** `core.catalog.origen.origenes_efectivos(session, lista)` (`core/catalog/origen.py:98`: el
`PrecioOrigen` de cada precio y, si falta, el de su lista) y `core.catalog.moneda.convertir`
(`core/catalog/moneda.py:55`) en vez de repetir esas consultas, siempre que las pruebas de la Tarea 22 sigan
pasando. No se reutiliza `core.catalog.precios.cambios_precio`: da variaciones en moneda nominal y solo entre listas
globales.

- [ ] **Step 1:** Escribir las tres pruebas de la Tarea 22 tal como están (Paso 1 de esa tarea). Valores: los de
  `tests/fixtures/memorias/atipicos_s3.md` §1–§5 (1, 2, 4…256, 257 → solo v8; …512 → vacío; 8 precios → abstención;
  720/36 y 1 100/44 → 0,25).
- [ ] **Step 2: Run → FAIL** — `uv run pytest tests/unit/test_series_atipicas.py tests/integration/test_atipicos.py
  tests/unit/test_ui_hoja_atipicos.py -W error -v` (módulos inexistentes).
- [ ] **Step 3:** Commit de las pruebas en rojo — `test(ml): series sembradas de RF-100 en rojo`.
- [ ] **Step 4:** Implementar `ml/anomaly/series.py`, `ui/atipicos.py` y el botón de la pestaña Precios según la
  Tarea 22, con la reutilización de *Interfaces*; agregar la entrada de `PROHIBIDOS_EN_UI`.
- [ ] **Step 5: Run → PASS** (mismo comando) y `uv run pytest tests/unit/test_arquitectura.py -W error`.
- [ ] **Step 6:** `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-6` → S3-6 en OK (anotar la
  salida).
- [ ] **Step 7:** Commit — `feat(ml): advertencia de variaciones de precio atipicas en la serie del insumo (RF-100)`.

### Task 1.2: reactivar la clave de IA desde el respaldo cifrado

**Subagente:** `silice-asistente-ia` · **Modelo:** Opus · **Esfuerzo:** high

**Files:**
- Modify: `asistente/clave.py` (métodos `pide_contrasena` y `reactivar`)
- Modify: `asistente/administracion.py` (función `reactivar_clave`)
- Modify: `ui/paginas/administracion.py` (sección y callback `_reactivar_clave`, junto a `_registrar_clave`)
- Test: `tests/unit/test_asistente_clave.py`, `tests/unit/test_asistente_administracion.py`,
  `tests/unit/test_ui_administracion_asistente.py` (existentes)

**Interfaces:**
- Consumes: `ClaveDeIA.activar(empresa_id, contrasena_respaldo=None)` (`asistente/clave.py:172`),
  `ClaveDeIA.hay_guardada(empresa_id)` (`:191`), `self._es_local` (regla del bucle local de `registrar`, `:149`),
  `seguridad.secretos` (`InvalidTag` y la lectura del respaldo), `_exigir(es_administrador)`
  (`asistente/administracion.py:30`), `cliente.operacion_sensible_permitida()`, `CLAVES_DEL_FORMULARIO`
  (`ui/paginas/administracion.py:451`).
- Produces:
  - `ClaveDeIA.pide_contrasena(self, empresa_id: str) -> bool`: `True` si `self._en_memoria is None`,
    `hay_guardada(empresa_id)` es verdadero y el almacén **no** tiene la clave (un error de almacén cuenta como «no
    la tiene»), es decir, solo queda el respaldo cifrado.
  - `ClaveDeIA.reactivar(self, empresa_id: str, contrasena: str, *, ip_cliente: str | None) -> str`: si
    `not self._es_local(ip_cliente)` → `ClaveNoRegistrable("La clave de IA solo se reactiva desde el propio
    equipo.")`; contraseña vacía → el mensaje que ya da `activar`; `InvalidTag` o respaldo ilegible (JSON dañado)
    → `ClaveNoRegistrable("La contraseña no abre el respaldo de la clave de IA.")` (solo esas causas, no
    `Exception` a secas); éxito → devuelve `ultimos_cuatro(clave)`.
  - `reactivar_clave(clave: ClaveDeIA, empresa_id: str, contrasena: str, *, es_administrador: bool, ip_cliente: str
    | None) -> str`: `_exigir(es_administrador)` y `clave.reactivar(...)`.
  - Clave de estado de la pantalla `"ia_contrasena_reactivar"`, agregada a `CLAVES_DEL_FORMULARIO`.

- [ ] **Step 1: Write the failing tests**
  - `test_pide_contrasena_solo_con_respaldo_y_sin_almacen` (almacén en memoria vacío + archivo de respaldo → True;
    con la clave en el almacén → False; con la clave ya en memoria → False).
  - `test_reactivar_con_la_contrasena_correcta_carga_la_clave` (`clave.vigente == <clave de prueba>`; devuelve los
    cuatro últimos caracteres).
  - `test_reactivar_con_contrasena_incorrecta_mensaje_fijo_y_sin_clave` (mensaje exacto; no contiene la
    contraseña; `clave.vigente is None`).
  - `test_reactivar_con_respaldo_danado_mensaje_fijo`.
  - `test_reactivar_desde_otro_equipo_se_rechaza` y `test_reactivar_sin_ser_administrador_sin_permiso`.
  - AppTest: `test_la_contrasena_de_reactivar_no_queda_en_la_pantalla` (tras pulsar,
    `st.session_state["ia_contrasena_reactivar"] == ""` y ningún valor del estado contiene la contraseña ni la clave).
  - AppTest: `test_la_seccion_solo_aparece_si_pide_contrasena` y
    `test_la_seccion_no_aparece_si_el_cliente_no_es_local`.
- [ ] **Step 2: Run → FAIL** — `uv run pytest tests/unit/test_asistente_clave.py
  tests/unit/test_asistente_administracion.py tests/unit/test_ui_administracion_asistente.py -W error`; commit
  `test(asistente): reactivar la clave de IA en rojo`.
- [ ] **Step 3: Implement** las firmas de *Produces*; la sección (solo para el administrador, solo si
  `pide_contrasena` y el cliente es local) muestra `text_input(type="password", key="ia_contrasena_reactivar")` y el
  botón «Reactivar la clave»; mensajes con `_avisar`/`texto_seguro`/`enmascarar` como `_registrar_clave`.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5:** Commit — `feat(asistente): reactivar la clave de IA desde el respaldo cifrado`.

### Task 1.3: las pruebas del experimento que faltan (seis pruebas y un fixture)

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

- [ ] **Step 1:** Leer las tres tareas y escribir cada prueba **como está especificada** (sus valores esperados son
  los oráculos escritos a mano entonces).
- [ ] **Step 2: Run** — `uv run pytest <los seis archivos> -W error -v`. El código ya existe: una prueba que falla
  **no se ajusta al código**. Se decide si es defecto del código (se informa al orquestador con la evidencia y se
  corrige en esta tarea con su commit `fix(...)`) o error del plan 0.9.0 (ruling registrado, con la cuenta corregida
  a mano).
- [ ] **Step 3:** Para cada archivo, anotar en el informe una mutación del código que la prueba atrapa.
- [ ] **Step 4:** Commit — `test(experimento): pruebas del comparador, metricas, mutaciones, corrida y congelado`.

### Task 1.4: informe del experimento sin gasto (RF-95, parcial)

**Subagente:** `silice-asistente-ia` · **Modelo:** Sonnet (excepción RS-7) · **Esfuerzo:** medium · **Después de 1.3**

**Files:**
- Create: `docs/resultados_asistente.md` (generado, **nunca editado a mano**)
- Modify (solo con ruling): `asistente/experimento/protocolo.json` y `asistente/experimento/congelado.json`

- [ ] **Step 1: Verificar el protocolo.** `uv run python -c "from asistente.experimento import congelado;
  print(congelado.verificar())"` → `[]`. `protocolo.json` declara `"modelo_local": "muse-glimmer"`: comprobar si
  existe en la biblioteca de Ollama **con uso de herramientas**. Si no existe, **no se cambia el protocolo en esta
  sesión** (exige volver a congelar y es decisión de Eugenio): se registra como bloqueo B-2 con una propuesta
  concreta (nombre, tamaño, fuente).
- [ ] **Step 2: Generar** con lo que no gasta: la medición controlada de mutaciones del auditor
  (`uv run python scripts/evaluar_asistente.py mutaciones …`) y luego `informe`. Las secciones de las corridas con
  Claude y con Ollama las escribe el script como **PENDIENTE**, con su bloqueo (B-1, B-2 de la ruta §6).
- [ ] **Step 3:** `uv run python scripts/meta_silice.py --version 0.9.0 --hasta S4-4` y anotar qué queda en OK y qué
  en PENDIENTE (con su bloqueo).
- [ ] **Step 4:** Commit — `docs(experimento): resultados de la medicion controlada (RF-95 parcial)`.

### Task 1.5: enmienda de la ERS

**Quién:** orquestador · **Modelo:** Opus · **Esfuerzo:** high

**Files:** Modify `docs/ERS.md`, `CHANGELOG.md`.

- [ ] **Step 1:** RF-100: incremento S3-6 → **1.1.0**, estado construido; RF-95: estado parcial con sus bloqueos.
- [ ] **Step 2:** Derogar la nota «Pruebas: en la auditoría final (regla del 2026-10-12)» (`docs/ERS.md:1417`) con
  una enmienda fechada que cite RS-2 de la ruta.
- [ ] **Step 3:** Reservar en la ERS el bloque de numeración libre (UC-26, RF-111, RNF-22 en adelante) para la ruta.
- [ ] **Step 4:** Commit — `docs(ers): enmienda 1.1.0 (RF-100, RF-95 parcial, pruebas obligatorias)`.

### Task 1.6: cierre de la 1.1.0

**Subagente:** `silice-escriba` · **Modelo:** Haiku · **Esfuerzo:** low (el orquestador corre la compuerta)

- [ ] **Step 1:** `pyproject.toml` → `version = "1.1.0"`; `uv lock`; `uv run python scripts/verificar_version.py`.
- [ ] **Step 2:** `CHANGELOG.md`: sección `1.1.0` (texto que dicta el orquestador).
- [ ] **Step 3:** Bitácora `docs/bitacora/2026-10-ruta-s1.md`: rulings, resultados, bloqueos y el cierre del hueco de
  T15 (`docs/bitacora/2026-10-silice-090.md:138-141`) con su commit (al dictado).
- [ ] **Step 4 (orquestador):** compuerta de la ruta §4 paso 6 (suite completa, ruff, guardia, metas
  `--version 0.8.0 --hasta S3-6` y `--version 0.9.0 --hasta S4-4`, revisores arquitectura, seguridad, requisitos,
  pruebas y hechos), PR, CI verde, fusión, etiqueta `v1.1.0`.
