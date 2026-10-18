# Sesión 4 — Gestor de producción de la arenera: existencias y báscula (Sílice 1.4.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la empresa sepa **cuánto hay y cuánto queda** de cada material de la arenera: materiales, movimientos
(producción, despacho de báscula, ajuste por conteo), existencia por fecha, importación de reportes de báscula con su
bandeja de pesajes sospechosos, rutas `/v1/produccion/*` y una pantalla de trabajo.

**Architecture:** Paquete nuevo `produccion/` (dominio puro con SQLAlchemy y openpyxl; no importa `core` salvo
`core.contracts`, ni `adapters`, `api`, `ui`). Sus tablas viven en la **base de la instalación** (revisión
`ins_0002_produccion`, ruling RT-S4-1). La API (`api/rutas/produccion.py`) pasa el archivo por la guardia de
`adapters.hoja_empresa.guardia` antes de entregarlo al lector. Pantalla en Streamlit mientras `frontend-desktop/` no
exista (RT-4); la versión React es la tarea 4.5, diferida.

**Tech Stack:** Python ≥ 3.12, SQLAlchemy 2, Alembic, FastAPI, openpyxl (solo lectura), pytest `-W error`.

**Spec:** [PLAN_GESTOR_PRODUCCION_Y_AUDITORIA_VISUAL.md](./PLAN_GESTOR_PRODUCCION_Y_AUDITORIA_VISUAL.md) §3, §6.3 y §7
con las enmiendas de su §0; orden y subagentes: [RUTA_SESIONES.md](./RUTA_SESIONES.md) §5 (sesión 4) y el ruling RT-7 de su §2;
cifras: [PLAN_FUENTES_DATOS_CANTERA.md](./PLAN_FUENTES_DATOS_CANTERA.md).

## Global Constraints

- `git diff origin/main -- core/` vacío; `uv run python scripts/guardia_nucleo.py --base origin/main` en OK.
- `Decimal` para pesos, volúmenes y cantidades; en base como texto (`String(40)`, igual que `DecimalExacto`); en la
  API como `str`; **nunca `float`**.
- **Ninguna cifra sin fuente** (PLAN_FUENTES §2): densidad, existencia inicial y mínima son **dato de la empresa**
  (sin valor por defecto en el código); toda constante del módulo se registra en `produccion/fuentes.py` con su estado
  y una prueba falla si una constante de cálculo está `A_COTEJAR` o `SIN_FUENTE`.
- Los reportes reales de báscula son confidenciales y **nunca** van al repositorio; los fixtures son construidos
  (`tests/fixtures/bascula/`), rotulados «ejemplo construido».
- La API no usa el reloj para decidir validez: la fecha de referencia («hoy» para detectar fechas futuras) la **manda
  el cliente** (como `fecha_devolucion` de `/v1/libros`).
- Archivos ajenos: pasan por `verificar_archivo` (`adapters/hoja_empresa/guardia.py:174`) antes de abrirse; tope de
  cuerpo 20 MiB (`api/proteccion.py`); el lector además limita filas y columnas (RNF-25).
- Toda ruta nueva lleva la clave de API (`CON_CLAVE` en `api/main.py`); nada se guarda fuera de `instalacion.db`.
- TDD con rojo visto (RS-2): la prueba va primero y se commitea en rojo; `pytest -W error`, cero omitidas. Commits
  convencionales en español, asunto sin tildes. Sin `git stash` simple.
- Versión SemVer menor **al fusionar** (RT-8): la siguiente libre en `main` (prevista 1.4.0); `pyproject.toml` se
  cambia en el último commit.
- La interfaz no usa colores sueltos ni cifras inventadas; los textos de usuario dicen qué hacer, no el nombre de una
  clase de error.

## Rulings de esta sesión (ratificables)

| # | Ruling | Por qué | Costo si es erróneo |
|---|---|---|---|
| RT-S4-1 | Las tablas de la arenera van en **`instalacion.db`** (revisión `ins_0002_produccion`, destino `instalacion`), no en un tercer destino `produccion.db`. | Un tercer destino obliga a tocar respaldo, instalador, lanzador y `__main__` (todos enumeran los dos destinos); la arenera es de la **empresa**, no de un caso, igual que las cuentas; el respaldo previo a migrar ya cubre la instalación. | Bajo: mover las tablas a otra base es una migración que copia filas. |
| RT-S4-2 | **Un despacho nunca se bloquea** por dejar la existencia negativa: se registra y el tablero lo marca «falta registrar producción o conteo». | La báscula pesa lo que sale de verdad; bloquear oculta el despacho y falsea la existencia. | Bajo. |
| RT-S4-3 | `silice-arenera` también es dueño de `ui/paginas/existencias.py` y `ui/existencias.py` (la ruta le asigna solo `produccion/`). | La pantalla es el entregable usable mientras no exista `frontend-desktop/`. | Bajo. |
| RT-S4-4 | El usuario de lo que escribe la API es la constante `USUARIO_API = "api (clave de API)"`: `exigir_clave_api` no entrega la identidad de la clave a la ruta. | No se toca `api/proteccion.py` en esta sesión. | Bajo: la bitácora de la pantalla sí lleva el usuario real. |
| RT-S4-5 | Los **sinónimos de encabezados** de la báscula (Ticket, Placa, Neto…) son un SUPUESTO_DECLARADO: sin muestras reales (B-4) solo se prueban con fixtures construidos y el detector admite un **mapeo explícito** del usuario. | PLAN_FUENTES C-8. | Medio: con muestras reales se ajustan los sinónimos. |
| RT-S4-6 | La unidad del peso (`kg` o `t`) se lee del encabezado; si no está, el archivo **no se importa** hasta que el usuario la indique. | Confundir kg con t es un error ×1000 que ningún validador detecta después. | Bajo. |

## Review Focus

1. **Peso en kg sin unidad en el encabezado** → no se importa nada; mensaje «Indique si los pesos están en kg o en t»
   (`test_sin_unidad_no_se_importa`).
2. **Reimportar el mismo reporte** (o uno con tickets repetidos) → no duplica despachos ni sospechosos
   (`test_reimportar_no_duplica`).
3. **Separador decimal** (`1.234,56`, `1,234.56`, `28,300` ambiguo) → los dos primeros se leen exactos; el tercero va
   a la bandeja como «número ambiguo» (`test_numeros_con_coma_y_punto`).
4. **Material de la báscula que no existe en el catálogo**, o en m³ sin densidad → bandeja «material desconocido» /
   «sin densidad», nunca un despacho en 0 (`test_material_sin_densidad_va_a_la_bandeja`).
5. **Archivo hostil** (CSV de 200 000 filas, `.xlsx` con macros renombrado, columnas de más) → rechazo con mensaje y
   sin tocar la base (`test_archivo_desmedido_se_rechaza`).

---

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `produccion/__init__.py` | Docstring del contexto; sin lógica. |
| `produccion/fuentes.py` | `EstadoDato`, `Constante`, `CONSTANTES`; qué constante del módulo tiene qué fuente. |
| `produccion/modelo.py` | `Base`, `METADATA_PRODUCCION`, tablas `prod_material`, `prod_movimiento`, `prod_pesaje_sospechoso`. |
| `produccion/inventario.py` | Servicio sobre `Session`: materiales, movimientos, existencia, tablero. |
| `produccion/conectores/detector_columnas.py` | Encabezados → `MapeoColumnas` (puro). |
| `produccion/conectores/bascula.py` | Bytes `.csv`/`.xlsx` → `LecturaBascula` (filas crudas validadas o sospechosas). |
| `produccion/importacion.py` | `LecturaBascula` → despachos y bandeja, idempotente; resolver y descartar sospechosos. |
| `migraciones/instalacion/versions/ins_0002_produccion.py` | DDL congelado de las tres tablas. |
| `api/rutas/produccion.py` | Rutas `/v1/produccion/*`. |
| `ui/existencias.py`, `ui/paginas/existencias.py` | Lógica sin Streamlit y la pantalla. |

---

### Task 4.0: plan, fuentes y arranque

**Quién:** orquestador (Opus, high) + `silice-rev-hechos` (Haiku, medium).

- [x] **Step 1:** Este plan, leyendo el código que fija las firmas (hecho 2026-10-18).
- [ ] **Step 2:** `silice-rev-hechos` recorre `PLAN_FUENTES_DATOS_CANTERA.md` §3 contra este plan: cada cifra o
  constante que el plan menciona tiene su fila de estado; devuelve discrepancias. Las fórmulas F-1/F-2 (costo horario)
  **no se cotejan en esta sesión**: la tarea 4.6 queda cerrada hasta tener la edición del libro en la mano.
- [ ] **Step 3:** Commit — `docs(planes): plan detallado de la sesion 4, existencias y bascula`.

### Task 4.1: enmienda de la ERS y del modelo de datos

**Quién:** orquestador (Opus, high). **Files:** Modify `docs/ERS.md`, `docs/modelo_datos.md`, `docs/plan_pruebas.md`;
Test `tests/unit/test_documentos_ruta_s4.py`.

**Produces:** UC-28 (existencias de la arenera), UC-29 (importar el reporte de báscula), RF-127 a RF-136 y RNF-25.

| RF | Requisito |
|---|---|
| RF-127 | Materiales de la arenera: código, nombre, unidad de venta (`m3` o `t`), densidad aparente (dato de la empresa, sin valor por defecto) y existencia mínima |
| RF-128 | Movimientos: producción (entrada), despacho y ajuste por conteo; existencia = Σ entradas − Σ despachos ± ajustes, por material y fecha |
| RF-129 | Tablero «cuánto hay y cuánto queda» con alerta «queda poco» (existencia ≤ mínima) y señal de existencia negativa (RT-S4-2) |
| RF-130 | Importar reportes de báscula `.xlsx`/`.csv` con detección de columnas, del separador decimal y de la unidad del peso (RT-S4-6) |
| RF-131 | Validar cada pesaje (tara ≥ bruto, neto ≠ bruto − tara, fecha futura o ilegible, número ambiguo, material desconocido o sin densidad) y enviar lo dudoso a la bandeja «Pesajes sospechosos» |
| RF-132 | Idempotencia: reimportar el mismo reporte no duplica despachos ni sospechosos |
| RF-133 | Resolver (con valores corregidos) o descartar un pesaje sospechoso, con usuario y fecha |
| RF-134 | Rutas `/v1/produccion/*` con clave de API; cantidades como texto |
| RF-135 | Pantalla «Existencias de la arenera» con permiso por rol (acción `OPERAR_ARENERA`) |
| RF-136 | Registro de constantes con estado de fuente; muestras reales de báscula nunca versionadas |
| RNF-25 | Límites al leer reportes ajenos: 20 MiB, 100 000 filas, 60 columnas, solo lectura |

- [ ] **Step 1: Write the failing test** `tests/unit/test_documentos_ruta_s4.py`: `test_la_ers_define_los_requisitos_de_la_sesion_4`
  lee `docs/ERS.md` y exige la presencia de cada código de `("UC‑28", "UC‑29", *[f"RF‑{n}" for n in range(127, 137)],
  "RNF‑25")` (con el guion no separable U+2011 que usa la ERS); `test_el_modelo_de_datos_nombra_las_tablas` exige
  `prod_material`, `prod_movimiento` y `prod_pesaje_sospechoso` en `docs/modelo_datos.md`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_documentos_ruta_s4.py -W error` → FAIL. Commit en rojo.
- [ ] **Step 3:** Escribir las entradas (UC con flujo principal y alternativos al formato de UC-25; tabla RF/RNF
  como la de UC-25; trazabilidad UC-28/29 → RF → sesión 4 de la ruta) y la sección de las tres tablas en
  `modelo_datos.md` (columnas de las tareas 4.2 y 4.3). Una línea en `plan_pruebas.md` con el oráculo del tablero.
- [ ] **Step 4:** Mismo comando → PASS. Commit — `docs(ers): UC-28 y UC-29, RF-127 a RF-136 y RNF-25 de la arenera`.

### Task 4.2: fuentes y modelo de `produccion/`

**Quién:** `silice-arenera` (Sonnet, medium). **Files:** Create `produccion/__init__.py`, `produccion/fuentes.py`,
`produccion/modelo.py`; Modify `tests/unit/test_arquitectura.py` (agregar `"produccion"` a
`PAQUETES_FUERA_DEL_NUCLEO` y una regla propia), `instalador/manifiesto.toml:21` y `instalador/manifiesto.py:32`
(el paquete viaja en el instalador), `migraciones/metadatos.py` (agregar `METADATA_PRODUCCION` a
`METADATAS_INSTALACION`). Test `tests/unit/test_produccion_modelo.py`, `tests/unit/test_produccion_fuentes.py`.

**Produces (firmas que usan las tareas siguientes):**

```python
# produccion/fuentes.py
class EstadoDato(StrEnum): VERIFICADO; DATO_DE_LA_EMPRESA; A_COTEJAR; CONSTRUIDO; A_MEDIR; SIN_FUENTE
@dataclass(frozen=True, slots=True)
class Constante: nombre: str; valor: str; estado: EstadoDato; fuente: str; usada_en_calculo: bool
CONSTANTES: tuple[Constante, ...]
# produccion/modelo.py  (todas las cantidades: DEC = String(40), Decimal en Python vía TypeDecorator propio `Cantidad`)
class Material:  id, codigo(UK, 40), nombre(120), unidad_venta('m3'|'t'), densidad_t_m3(Cantidad|None),
                 existencia_minima(Cantidad), activo(bool)
class Movimiento: id, material_id(FK), fecha(Date), tipo('entrada'|'despacho'|'ajuste'), cantidad(Cantidad,
                 en unidad_venta; >0 en entrada/despacho, distinta de 0 y con signo en ajuste), ticket(String(60)|None),
                 placa, cliente, nota, origen('manual'|'bascula'), usuario, registrado(DateTime)
class PesajeSospechoso: id, huella_archivo(64), fila(int), ticket, fecha_texto, placa, material_texto, bruto_texto,
                 tara_texto, neto_texto, motivo(String(200)), estado('pendiente'|'resuelto'|'descartado'),
                 resuelto_por, resuelto_en(DateTime|None)
```

`CheckConstraint`s: `tipo IN (...)`, `unidad_venta IN ('m3','t')`, `cantidad` no vacía; índice único parcial no
existe en SQLite → `UniqueConstraint("ticket")` (los `NULL` no chocan). `densidad_t_m3` > 0 si no es nulo se valida en
el servicio, no en el DDL.

**Reglas de arquitectura** (`test_arquitectura.py`): `produccion/` importa solo biblioteca estándar, `sqlalchemy`,
`openpyxl` y `core.contracts`; **prohibido** `core.*` restante, `adapters`, `api`, `ui`, `operacion`, `seguridad`.

- [ ] **Step 1: Write the failing tests.** `test_produccion_modelo.py`: `test_las_tres_tablas_existen_con_sus_columnas`
  (`create_all` sobre `sqlite://` y se comparan nombres de columnas con la lista de arriba),
  `test_un_ticket_repetido_choca` (dos `Movimiento` con `ticket="TCK-1"` → `IntegrityError`),
  `test_dos_movimientos_sin_ticket_conviven`, `test_la_cantidad_conserva_los_decimales`
  (`Decimal("28.300")` → vuelve `Decimal("28.300")`), `test_tipo_invalido_choca`.
  `test_produccion_fuentes.py`: `test_ninguna_constante_de_calculo_es_a_cotejar_ni_sin_fuente` recorre `CONSTANTES`.
  En `test_arquitectura.py`: `test_produccion_respeta_su_regla` con un archivo que importe `core.models` →
  falla (usar `tmp_path`, como las guardias vecinas).
- [ ] **Step 2:** `uv run pytest tests/unit/test_produccion_modelo.py tests/unit/test_produccion_fuentes.py
  tests/unit/test_arquitectura.py -W error` → FAIL. Commit en rojo — `test(produccion): modelo y fuentes en rojo`.
- [ ] **Step 3:** Implementar `fuentes.py`, `modelo.py` (tipo `Cantidad(TypeDecorator)` propio con la misma
  semántica que `core.models.tipos.DecimalExacto`: texto, `TypeError` si no es `Decimal`; **no se importa de `core`**).
  `CONSTANTES` trae: `MAX_FILAS=100000` (CONSTRUIDO), `MAX_COLUMNAS=60` (CONSTRUIDO), `FILAS_DE_ENCABEZADO=30`
  (CONSTRUIDO), `TOLERANCIA_NETO_T=0` (CONSTRUIDO: la báscula entrega enteros en kg). Ninguna es `A_COTEJAR`.
- [ ] **Step 4:** Mismos comandos → PASS; `uv run ruff check produccion migraciones tests`.
- [ ] **Step 5:** Commit — `feat(produccion): modelo de materiales, movimientos y pesajes sospechosos`.

### Task 4.3: migración `ins_0002_produccion`

**Quién:** `silice-base-datos` (Sonnet, medium). **Files:** Create
`migraciones/instalacion/versions/ins_0002_produccion.py`; Test `tests/integration/test_migracion_produccion.py`.

**Consumes:** `produccion.modelo.METADATA_PRODUCCION` (4.2). **Produces:** `revision_head(Destino.INSTALACION) ==
"ins_0002_produccion"`.

- [ ] **Step 1: Write the failing test.** `test_migrar_crea_las_tablas_y_cero_deriva` (`aplicar_revisiones(ruta,
  Destino.INSTALACION)` y `instantanea_esquema` igual a la de `create_all` de `METADATAS_INSTALACION`, patrón de
  `tests/integration/test_migracion_instalacion.py`); `test_la_base_de_la_1_0_0_se_respalda_y_migra` (parte de una
  base en `ins_0001_seguridad` con una cuenta, `preparar_base` → cuenta intacta, juego de respaldo creado, tablas
  nuevas vacías); `test_deshacer_vuelve_a_ins_0001`.
- [ ] **Step 2:** `uv run pytest tests/integration/test_migracion_produccion.py tests/integration/test_migraciones.py
  -W error` → FAIL. Commit en rojo.
- [ ] **Step 3:** Escribir la revisión con DDL literal (`down_revision = "ins_0001_seguridad"`), `DEC = sa.String(40)`
  como en `caso_0002`; `downgrade` borra las tres tablas en orden inverso de dependencia.
- [ ] **Step 4:** PASS; además `uv run pytest tests/integration/test_preparar_base.py tests/integration/test_respaldo.py
  -W error` (ninguna asumía una sola revisión de instalación; si alguna sí, se corrige su expectativa).
- [ ] **Step 5:** Commit — `feat(migraciones): ins_0002_produccion, tablas de la arenera en la instalacion`.

### Task 4.4: servicio de inventario

**Quién:** `silice-arenera` (Sonnet, medium). **Files:** Create `produccion/inventario.py`; Test
`tests/unit/test_produccion_inventario.py`.

**Consumes:** modelo de 4.2. **Produces:**

```python
class ErrorDeInventario(ValueError): ...
@dataclass(frozen=True, slots=True)
class FilaExistencia: material: Material; existencia: Decimal; minima: Decimal
                      queda_poco: bool; negativa: bool
def crear_material(sesion, *, codigo, nombre, unidad_venta, existencia_minima, densidad_t_m3=None) -> Material
def registrar_entrada(sesion, material_id, fecha, cantidad, *, usuario, nota="") -> Movimiento
def registrar_despacho(sesion, material_id, fecha, cantidad, *, usuario, ticket=None, placa="",
                       cliente="", origen="manual", nota="") -> Movimiento
def registrar_ajuste_por_conteo(sesion, material_id, fecha, conteo_fisico, *, usuario, nota="") -> Movimiento | None
def existencia(sesion, material_id, a_fecha: date | None = None) -> Decimal
def tablero(sesion, a_fecha: date | None = None) -> list[FilaExistencia]   # solo activos, por código
```

Semántica: `existencia` suma movimientos con `fecha <= a_fecha` (entradas +, despachos −, ajustes con su signo).
`registrar_ajuste_por_conteo` guarda `conteo_fisico − existencia(a esa fecha)` y devuelve `None` si la diferencia es 0.
Cantidades ≤ 0 en entrada/despacho, `unidad_venta` fuera de `m3`/`t`, código repetido, densidad ≤ 0 →
`ErrorDeInventario` con mensaje para el usuario. `queda_poco = existencia <= minima`; `negativa = existencia < 0`.

- [ ] **Step 1: Write the failing tests** (oráculo a mano, base `sqlite://` con `create_all`). Serie del oráculo para
  «Arena lavada» (`ARENA`, m3, mínima 20, **ejemplo construido**): entrada 100 (1-oct), despacho 30 (2-oct), despacho
  45,5 (3-oct), entrada 10 (4-oct), conteo 40 (5-oct). Esperado: existencia al 2-oct 70; al 3-oct 24,5; al 4-oct
  34,5; el ajuste del 5-oct es **+5,5** y la existencia al 5-oct es 40; `existencia(a_fecha=None)` = 40.
  Pruebas: `test_existencia_por_fecha_con_la_serie_a_mano`, `test_el_ajuste_guarda_la_diferencia_con_signo`
  (conteo 20 al 5-oct → ajuste −14,5), `test_conteo_igual_a_lo_teorico_no_crea_ajuste`,
  `test_queda_poco_incluye_el_minimo_exacto` (existencia = 20 → `True`), `test_despacho_que_deja_negativo_se_registra_y_marca`
  (RT-S4-2), `test_cantidad_cero_o_negativa_se_rechaza`, `test_codigo_repetido_se_rechaza`,
  `test_tablero_omite_materiales_inactivos`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_produccion_inventario.py -W error` → FAIL. Commit en rojo.
- [ ] **Step 3:** Implementar; la suma se hace en Python con `Decimal` (los valores son texto en la base).
- [ ] **Step 4:** PASS + `ruff`. Commit — `feat(produccion): existencias por material y fecha y tablero con alerta de minimo`.

### Task 4.5: fixtures de báscula (oráculo independiente)

**Quién:** `silice-pruebas` (Sonnet, high). **Files:** Create `tests/fixtures/bascula/__init__.py`,
`tests/fixtures/bascula/construir.py`, `tests/fixtures/bascula/ORACULO.md`.

**Produces:** `construir.csv_basico() -> bytes`, `construir.xlsx_basico() -> bytes`,
`construir.xlsx_sin_unidad() -> bytes`, `construir.csv_coma_decimal() -> bytes`,
`construir.xlsx_con_macros_renombrado() -> bytes`, `construir.csv_desmedido(filas: int) -> bytes`; y `ORACULO.md`
con, **a mano**, qué debe salir de cada uno.

Reporte básico (ejemplo construido, encabezados `Ticket; Fecha; Placa; Cliente; Material; Bruto (kg); Tara (kg);
Neto (kg)`), 6 filas, con este oráculo:

| Fila | Ticket | Hecho | Resultado esperado |
|---|---|---|---|
| 1 | TCK-001 | 42 500 / 14 200 / 28 300 kg, `ARENA` | despacho 28,300 t → en m³ con densidad del fixture 1,60: 17,6875 |
| 2 | TCK-002 | 38 000 / 13 500 / 24 500, `PIEDRA34` (unidad `t`) | despacho 24,5 t |
| 3 | TCK-003 | tara 45 000 > bruto 42 000 | sospechoso «tara mayor o igual que el bruto» |
| 4 | TCK-004 | neto 20 000 ≠ 40 000 − 15 000 | sospechoso «neto distinto de bruto − tara» |
| 5 | TCK-005 | fecha 2026-12-31 con referencia 2026-10-18 | sospechoso «fecha futura» |
| 6 | TCK-006 | material `GRAVA9` no registrado | lo lee el lector; la importación lo manda a la bandeja «material desconocido» |

(La densidad 1,60 t/m³ es del **fixture**, rotulada «ejemplo construido»; no es un valor del producto. Tampoco es coherente a propósito con el 1,65 de PLAN_FUENTES C-5/C-6: ese es otro ejemplo y no se mezclan.)

- [ ] **Step 1:** Escribir `ORACULO.md` **antes** que los generadores (los valores arriba, más los de las otras cinco
  variantes: kg sin unidad; `1.234,56` y `1,234.56`; `28,300` ambiguo; macros renombrado; 200 000 filas).
- [ ] **Step 2:** Escribir los generadores con `openpyxl` y `csv`; `xlsx_con_macros_renombrado` es un ZIP con
  `xl/vbaProject.bin` y extensión `.xlsx`.
- [ ] **Step 3:** `uv run pytest tests/unit/test_fixtures_bascula.py -W error` (prueba que cada generador devuelve
  bytes, que el básico tiene 6 filas de datos y que los dos formatos coinciden celda a celda) → PASS.
- [ ] **Step 4:** Commit — `test(produccion): fixtures construidos de bascula con su oraculo a mano`.

### Task 4.6: detector de columnas y lector de báscula

**Quién:** `silice-arenera` (Sonnet, high). **Files:** Create `produccion/conectores/__init__.py`,
`produccion/conectores/detector_columnas.py`, `produccion/conectores/bascula.py`; Test
`tests/unit/test_conector_bascula.py`, `tests/unit/test_detector_columnas.py`.

**Consumes:** fixtures de 4.5. **Produces:**

```python
# detector_columnas.py
CAMPOS = ("ticket", "fecha", "placa", "cliente", "material", "bruto", "tara", "neto")
@dataclass(frozen=True, slots=True)
class MapeoColumnas:
    columnas: Mapping[str, int]      # campo → índice 0-based
    fila_encabezado: int             # 0-based
    unidad_peso: str | None          # "kg" | "t" | None
def detectar(filas: Sequence[Sequence[object]]) -> MapeoColumnas   # raise MapeoNecesario si faltan ticket, fecha, material o peso
class MapeoNecesario(ValueError): faltan: tuple[str, ...]
# bascula.py
@dataclass(frozen=True, slots=True)
class PesajeLeido: fila: int; ticket: str; fecha: date; placa: str; cliente: str; material: str
                   bruto_t: Decimal; tara_t: Decimal; neto_t: Decimal
@dataclass(frozen=True, slots=True)
class PesajeDudoso: fila: int; ticket: str; fecha_texto: str; placa: str; material: str
                    bruto_texto: str; tara_texto: str; neto_texto: str; motivo: str
@dataclass(frozen=True, slots=True)
class LecturaBascula: huella: str; pesajes: tuple[PesajeLeido, ...]; dudosos: tuple[PesajeDudoso, ...]
class ReporteRechazado(ValueError): ...      # mensaje para el usuario
def leer(datos: bytes, nombre: str, *, fecha_referencia: date, unidad_peso: str | None = None,
         mapeo: Mapping[str, int] | None = None) -> LecturaBascula
```

Reglas: la extensión (`.csv` o `.xlsx`) decide el lector; CSV en UTF-8 con o sin BOM, o Latin-1 si no decodifica; el
delimitador `;`, `,` o tabulador se detecta con `csv.Sniffer` sobre las primeras 4 KiB; XLSX con
`openpyxl.load_workbook(read_only=True, data_only=True)`, primera hoja. Encabezados normalizados (sin tildes,
minúsculas, sin signos); la unidad sale de `(kg)`, `kg`, `ton`, `(t)`, `toneladas` en el encabezado del peso.
Pesos a **toneladas** (`kg / 1000`, `Decimal`). Las celdas numéricas nativas de XLSX no son ambiguas; el texto con un
solo separador y exactamente tres cifras tras él (`28,300`) es **ambiguo**. `huella` = SHA-256 de `datos`. Más de
`MAX_FILAS` filas o `MAX_COLUMNAS` columnas → `ReporteRechazado`. Sin `unidad_peso` ni unidad en el encabezado →
`ReporteRechazado("Indique si los pesos están en kg o en t.")`. Tickets repetidos dentro del archivo: el primero se
lee, los demás van a `dudosos` con «ticket repetido en el archivo».

- [ ] **Step 1: Write the failing tests** (nombres exactos): `test_detecta_las_ocho_columnas_del_reporte_basico`,
  `test_sinonimos_de_encabezado` (`Boleto`, `N° Ticket`, `Placa del camión`, `Peso Neto (t)`),
  `test_faltan_columnas_pide_mapeo` (`MapeoNecesario.faltan == ("material",)`), `test_xlsx_y_csv_dan_lo_mismo`
  (`leer(csv_basico()…) == leer(xlsx_basico()…)` salvo `huella`), `test_pesajes_del_oraculo` (las seis filas de
  `ORACULO.md`: el lector da tres leídos y tres dudosos con su motivo exacto; la fila 6 la decide la importación), `test_sin_unidad_no_se_importa`,
  `test_numeros_con_coma_y_punto` (`1.234,56`→`Decimal("1234.56")`, `1,234.56`→`Decimal("1234.56")`, `28,300`→
  dudoso «número ambiguo»), `test_archivo_desmedido_se_rechaza` (200 000 filas), `test_mapeo_explicito_manda`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_conector_bascula.py tests/unit/test_detector_columnas.py -W error`
  → FAIL. Commit en rojo — `test(produccion): lector de bascula en rojo`.
- [ ] **Step 3:** Implementar. La validación de neto es exacta (`TOLERANCIA_NETO_T = 0` de `fuentes.py`); si falta la
  columna `neto` se calcula `bruto − tara` y no hay regla D.
- [ ] **Step 4:** PASS + `ruff`. Commit — `feat(produccion): detector de columnas y lector de reportes de bascula`.

### Task 4.7: importación idempotente y bandeja

**Quién:** `silice-arenera` (Sonnet, high). **Files:** Create `produccion/importacion.py`; Test
`tests/integration/test_produccion_importacion.py`.

**Consumes:** `LecturaBascula` (4.6), `registrar_despacho` y `Material` (4.2, 4.4). **Produces:**

```python
@dataclass(frozen=True, slots=True)
class ResultadoImportacion: registrados: int; ya_registrados: int; a_la_bandeja: int; huella: str
def importar(sesion, lectura: LecturaBascula, *, usuario: str) -> ResultadoImportacion
def pendientes(sesion) -> list[PesajeSospechoso]
def resolver(sesion, id_sospechoso: int, *, material_codigo: str, fecha: date, neto_t: Decimal,
             ticket: str, usuario: str, ahora: datetime) -> Movimiento
def descartar(sesion, id_sospechoso: int, *, usuario: str, ahora: datetime) -> None
```

Semántica: el material se busca por **código** o por **nombre** normalizado; el despacho se guarda en la unidad de
venta del material (`t` tal cual; `m3` = `neto_t / densidad_t_m3`, redondeo `ROUND_HALF_EVEN` a 4 decimales; sin
densidad → bandeja «material sin densidad»). Un pesaje cuyo `ticket` ya existe como `Movimiento` cuenta en
`ya_registrados` y no se toca; un dudoso con la misma `(huella, fila)` ya en bandeja no se vuelve a insertar. Todo en
una transacción: si algo falla, no queda nada. `resolver` y `descartar` solo actúan sobre `pendiente`.

- [ ] **Step 1: Write the failing tests** (base `sqlite://`; materiales `ARENA` m3 densidad 1,60 y `PIEDRA34` t, **ejemplo
  construido**; lectura del fixture 4.5): `test_importar_el_basico_registra_dos_y_manda_cuatro_a_la_bandeja`
  (despacho de ARENA = `Decimal("17.6875")`, de PIEDRA34 = `Decimal("24.5")`), `test_reimportar_no_duplica`
  (segunda corrida: `registrados=0, ya_registrados=2, a_la_bandeja=0`, 4 pendientes en total),
  `test_material_sin_densidad_va_a_la_bandeja`, `test_resolver_crea_el_despacho_y_cierra_el_sospechoso`,
  `test_descartar_no_crea_despacho`, `test_resolver_dos_veces_se_rechaza`, `test_un_fallo_deja_todo_como_estaba`
  (`ticket` de un movimiento forzado a chocar a mitad → nada nuevo en la base), `test_existencia_final_con_la_serie_a_mano`
  (entrada de 100 m³ de ARENA + el despacho importado → 82,3125).
- [ ] **Step 2:** `uv run pytest tests/integration/test_produccion_importacion.py -W error` → FAIL. Commit en rojo.
- [ ] **Step 3:** Implementar con `sesion.begin_nested()` por importación.
- [ ] **Step 4:** PASS + `ruff`. Commit — `feat(produccion): importacion idempotente de pesajes y bandeja de sospechosos`.

### Task 4.8: rutas `/v1/produccion/*`

**Quién:** `silice-backend` (Sonnet, high). **Files:** Create `api/rutas/produccion.py`; Modify `api/main.py` (agregar
el `include_router` con `CON_CLAVE`), `api/dependencias.py` (agregar `SesionInstalacionDep`, sesión de
`operacion.instalacion.sesion_de_instalacion`), `docs/api.json` (regenerar, no editar a mano); Test
`tests/integration/test_api_produccion.py`.

**Rutas** (prefijo `/v1/produccion`, todas con clave; cantidades como `str`; errores `{"detalle": ...}`):

| Método y ruta | Cuerpo / parámetros | Respuesta |
|---|---|---|
| `GET /materiales` | — | lista de materiales |
| `POST /materiales` | `codigo, nombre, unidad_venta, existencia_minima, densidad_t_m3?` | 201 + material; código repetido 409; datos inválidos 422 |
| `POST /movimientos` | `material_codigo, tipo, fecha, cantidad, nota?` (`entrada`, `despacho` o `ajuste` con `cantidad` = **conteo físico**) | 201 + movimiento (el ajuste devuelve el de la diferencia; 200 con `null` si no hay diferencia) |
| `GET /existencias` | `a_fecha?` (ISO) | filas de `tablero` |
| `POST /bascula/importar` | multipart `archivo`, `fecha_referencia` (ISO, **obligatoria**), `unidad_peso?` (`kg`/`t`), `mapeo?` (JSON campo → índice) | `ResultadoImportacion`; extensión equivocada 415; cuerpo > 20 MiB 413; `ReporteRechazado`, `ArchivoRechazado`, `MapeoNecesario` 422 con su mensaje; otro fallo 500 con mensaje fijo y detalle solo en el registro |
| `GET /pesajes-sospechosos` | — | pendientes |
| `POST /pesajes-sospechosos/{id}/resolver` | `material_codigo, fecha, neto_t, ticket, ahora` | 201 + movimiento; ya resuelto 409 |
| `POST /pesajes-sospechosos/{id}/descartar` | `ahora` | 204 |

`usuario` = `USUARIO_API` (RT-S4-4). El `.xlsx` pasa por `verificar_archivo` en un hilo (`run_in_threadpool`) antes
de `leer`. Un `.csv` no pasa por la guardia (no es ZIP) pero sí por el tope de filas del lector.

- [ ] **Step 1: Write the failing tests** (`TestClient`, clave de API de prueba como en `tests/integration/test_api_clave.py`,
  `SILICE_DATOS` en `tmp_path` por `tests/conftest.py`): `test_sin_clave_toda_ruta_responde_401` (parametrizada por
  ruta), `test_crear_material_y_registrar_el_flujo_de_la_serie_a_mano` (la serie de 4.4: `GET /existencias` →
  `Decimal(fila["existencia"]) == Decimal("40")`; se compara como `Decimal`, no como texto),
  `test_importar_el_reporte_basico_por_la_api` (`registrados == 2`, `a_la_bandeja == 4`),
  `test_importar_sin_unidad_responde_422_con_el_mensaje`, `test_archivo_con_macros_renombrado_responde_422`,
  `test_extension_equivocada_responde_415`, `test_resolver_y_descartar`, `test_las_cantidades_viajan_como_texto`.
- [ ] **Step 2:** `uv run pytest tests/integration/test_api_produccion.py -W error` → FAIL. Commit en rojo.
- [ ] **Step 3:** Implementar. Esquemas Pydantic con `str` para toda cantidad y `Decimal(texto)` en la frontera.
- [ ] **Step 4:** PASS; `uv run python scripts/exportar_openapi.py` y `git diff --stat docs/api.json`;
  `uv run pytest tests/integration -k "api" -W error`. Commit — `feat(api): rutas de la arenera, existencias y bascula`.

### Task 4.9: pantalla «Existencias de la arenera»

**Quién:** `silice-arenera` (Sonnet, medium; RT-S4-3). **Files:** Create `ui/existencias.py`,
`ui/paginas/existencias.py`; Modify `seguridad/permisos.py` (agregar `Accion.OPERAR_ARENERA` =
`frozenset({ARMA, ADMINISTRADOR})`), `ui/app.py` (una `DefinicionPagina` en `SECCION_TRABAJO`, caso de uso
`"UC-28 / UC-29"`), `tests/unit/test_arquitectura.py` (`PROHIBIDOS_EN_UI["ui/existencias.py"] = ("streamlit",
"pandas")`); Test `tests/unit/test_ui_existencias.py`, `tests/unit/test_permisos.py` (agregar la fila).

**Produces** (`ui/existencias.py`, sin Streamlit): `tablero_para_pantalla(sesion, a_fecha) -> list[FilaPantalla]` con
`FilaPantalla(codigo, nombre, unidad, existencia_texto, minima_texto, estado)` y `estado ∈ {"normal", "queda poco",
"negativa"}`; `importar_desde_pantalla(sesion, datos, nombre, fecha_referencia, unidad_peso, usuario) ->
ResultadoImportacion`. La página tiene cuatro pestañas: **Existencias** (tabla con el estado en **texto e ícono**, no
solo color; IBCS: favorable/desfavorable, no verde/rojo sueltos), **Registrar** (entrada, despacho, conteo),
**Importar báscula** (zona de carga y resultado) y **Pesajes sospechosos** (resolver o descartar). Cada acción vuelve a
exigir `OPERAR_ARENERA`; los mensajes de error son los de `ErrorDeInventario`/`ReporteRechazado`, nunca una traza.

- [ ] **Step 1: Write the failing tests:** `test_tablero_para_pantalla_marca_el_estado` (serie de 4.4: mínima 20 y
  existencia 24,5 → `normal`; 20 → `queda poco`; −3 → `negativa`), `test_la_pagina_exige_el_permiso`
  (`AppTest`, rol `revisa` → mensaje de falta de permiso, sin tabla), `test_la_pagina_muestra_la_tabla_para_arma`,
  `test_navegacion_incluye_la_pagina_solo_para_quien_puede`, y la fila de la matriz en `test_permisos.py`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_ui_existencias.py tests/unit/test_permisos.py
  tests/unit/test_arquitectura.py tests/unit/test_ui_app.py -W error` → FAIL. Commit en rojo.
- [ ] **Step 3:** Implementar. La sesión sale de `operacion.instalacion.sesion_de_instalacion()`; el usuario, de la
  sesión de la interfaz (`ui.sesion`).
- [ ] **Step 4:** PASS + `ruff`. Commit — `feat(ui): pantalla de existencias de la arenera con alerta de minimo y bandeja`.

### Task 4.10: prueba de extremo a extremo

**Quién:** `silice-pruebas` (Sonnet, high). **Files:** Test `tests/integration/test_produccion_extremo.py`.

- [ ] **Step 1:** Escribir `test_de_la_importacion_al_tablero_por_la_api`: crear `ARENA` (m3, densidad 1,60, mínima 20)
  y `PIEDRA34` (t, mínima 10), entrada de 100 m³ de ARENA, importar `xlsx_basico()` con referencia 2026-10-18 y
  `unidad_peso` ausente (la toma del encabezado), resolver TCK-006 con `GRAVA9→PIEDRA34` y neto 18,0 t; esperado:
  ARENA 82,3125 m³ (`normal`), PIEDRA34 −24,5 −18,0 = **−42,5 t** (`negativa`, RT-S4-2) y 3 sospechosos pendientes.
  `test_respaldo_y_migracion_conservan_las_existencias` (la base se llena, se respalda con `operacion.respaldo` y
  se restaura: mismo tablero).
- [ ] **Step 2:** Correr → PASS (los servicios existen: si falla, es un hallazgo y se corrige en su tarea). Commit —
  `test(produccion): de la importacion al tablero por la api`.

### Task 4.11: cierre de la sesión (compuerta)

**Quién:** `silice-escriba` (Haiku, low) para lo mecánico; orquestador (Opus) para los rulings.
**Files:** Modify `CHANGELOG.md` (líneas bajo «Sin publicar»), `pyproject.toml` (versión al fusionar),
`docs/manual_usuario.md` (sección «Existencias de la arenera»), `docs/plan_pruebas.md`; Create
`docs/bitacora/2026-10-ruta-s4.md`.

- [ ] **Step 1:** `git fetch && git merge origin/main`; regenerar `docs/api.json`; traer la cabeza de Alembic
  vigente (si otra sesión agregó `ins_0003_*`, re-apuntar `down_revision`).
- [ ] **Step 2:** Suite completa **una vez** (~40 min; no corre en dos sesiones a la vez): `uv run pytest -W error
  --junitxml=reporte-pruebas.xml` y `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml`; `uv run ruff
  check .`; `uv run python scripts/guardia_nucleo.py --base origin/main`. Esperado: todo verde, cero omitidas, guardia OK.
- [ ] **Step 3:** Revisores (§3.2 de la ruta): arquitectura, requisitos, pruebas, diseño y hechos; **todos aprueban**
  (los bloqueantes se corrigen y se vuelve a pasar). Seguridad revisa solo la lectura de archivos ajenos (RNF-25).
- [ ] **Step 4:** Versión, CHANGELOG, bitácora (rulings RT-S4-1 a RT-S4-6, bloqueos B-4 y 4.6, diferidos 4.5/4.6).
- [ ] **Step 5:** Push, PR con CI verde (Linux, Windows, calidad), fusión con merge commit; encadenar la sesión
  siguiente que Eugenio tenga habilitada.

---

## Diferido y bloqueos (anotar en la bitácora)

| Qué | Motivo | Se reabre cuando |
|---|---|---|
| 4.5 Tablero React (`TableroExistencias`, `DropzoneBascula`) | `frontend-desktop/` aún no existe (sesión 2) | la sesión 2 esté en `main` |
| 4.6 Partes diarios, costo horario, `InsumoCanteraDTO` | F-1 y F-2 siguen «A COTEJAR»; sin fichas de maquinaria | fuentes verificadas + fichas de la empresa |
| B-4 Muestras reales de báscula | solo la empresa las tiene | Eugenio las anonimiza con `scripts/anonimizar_libro.py` (o su equivalente para CSV) y se ajustan los sinónimos |

## Self-review

- **Cobertura de la ruta §5 sesión 4:** 4.0 (esta), 4.1 → 4.2/4.4, 4.2 → 4.3, 4.3 → 4.6/4.7, 4.4 → 4.8, 4.5 → 4.9
  (Streamlit; la React diferida), 4.6 diferida con motivo. RF-127…RF-136 y RNF-25 tienen tarea y prueba.
- **Consistencia de nombres:** `Material`, `Movimiento`, `PesajeSospechoso`, `LecturaBascula`, `ResultadoImportacion`
  y `USUARIO_API` se usan igual en 4.2, 4.4, 4.6, 4.7, 4.8 y 4.10.
- **Proporción:** el plan nombra firmas, valores y oráculos; el código lo escriben los subagentes.
