# AREN.IA — la pantalla de composición (P2.2–P2.4) y la hoja de ruta de P3 a P5

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Terminar la fase P2 — la pantalla donde una persona compone un APU a mano, con desglose en
vivo, buscador de la referencia MaPreX y las cuatro ayudas de aprendizaje automático— y dejar
declarada, con sus condiciones de entrada, la hoja de ruta de las fases P3, P4 y P5.

**Architecture:** `ui/composicion.py` ya contiene las funciones puras y es donde sigue viviendo toda
la lógica; `ui/paginas/componer.py` solo pinta. Esa separación no es estética: hoy el repositorio no
tiene ninguna prueba de interfaz, así que lo único verificable es lo que se puede llamar sin
Streamlit. Las cuatro ayudas se invocan con importación perezosa para que la interfaz siga
arrancando sin el extra `ml`. Ninguna tarea de este plan toca `core/`.

**Tech Stack:** Python 3.12 · `Decimal` · Streamlit · SQLAlchemy 2 · pytest · ruff · uv

**Spec:**
[docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md](../specs/2026-09-16-prototipo-composicion-apu-design.md)

**Plan de sesiones:** [PLAN_PROTOTIPO.md](../../../PLAN_PROTOTIPO.md) — este documento desarrolla
las sesiones **P2.2, P2.3 y P2.4**, y declara la hoja de ruta de P3 a P5 sin convertirla en tareas,
por la razón que se explica en su propia sección.

**Plan anterior:**
[2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion.md](2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion.md)
— saldó las dos deudas de P1 y escribió `ui/composicion.py`. Su auditoría final dejó tres lecciones
que este plan incorpora como restricciones, no como sugerencias.

## Situación de partida

- Rama `inc/PLAN-prototipo`, 10 commits sobre `p-base` (`471b3e2`), **sin empujar**.
- Meta del sprint: **7/12**. Meta de fase `--hasta P2`: **7/8**, con **P8 pendiente**.
- Suite: 598 pruebas, 0 omitidas, cobertura de `core/` al 98 %, los siete gates de la CI en verde.
- `ui/composicion.py` existe, no importa `streamlit` ni `pandas`, y expone:
  `ComposicionInvalida(ValueError)`, `decimal_desde_texto(texto, campo)`,
  `composicion_desde_tablas(...)` e `item_desde_cantidad(..., dominio)`.
- `Catalogo.cargar_composicion` y `Catalogo.reemplazar_composicion` exigen **ambas** un quinto
  argumento `condiciones: str` y lanzan `ValueError` si viene vacío (RF‑33).

## Global Constraints

- **`Decimal` en todo lo monetario y dimensional.** Nunca `float` en cantidades, precios, factores
  ni rendimientos. Se construye siempre desde texto: `Decimal("6")`, nunca `Decimal(6.0)`.
- **Se redondea solo al presentar.** El único sitio del núcleo que redondea es `core/budget/excel.py`.
- **`tests/unit/test_costing.py` y `tests/fixtures/apu_linea_base.py` NO se modifican.**
- **Ninguna tarea de este plan toca `core/`.** Si una parece exigirlo, la tarea está mal: detente y
  reporta. `core/contracts/` está declarado estable por `CLAUDE.md` §5.
- **`ui/composicion.py` no importa `streamlit` ni `pandas`**, ni siquiera dentro de una función. Es
  la meta P7 y se comprueba por búsqueda de texto.
- **Toda sesión que añada o cambie una columna del esquema declara antes qué pasa con las bases ya
  creadas** (`docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md`). Ninguna tarea de este plan
  cambia el esquema; si alguna parece necesitarlo, para y reporta.
- **Los mensajes de error nombran la tabla y el índice de fila en base 1**, y la descripción cuando
  exista. Es la lección de la auditoría anterior: con tres tablas dinámicas en pantalla, un mensaje
  sin fila no dice dónde mirar.
- **La conversión de `DataFrame` a lista de diccionarios es trabajo de la página**, no del módulo de
  funciones puras. `ui/composicion.py` recibe `Sequence[Mapping[str, str]]` y ya normaliza `None` y
  `NaN`; la página no debe volver a hacerlo.
- ruff: `line-length = 100`, `target-version = "py312"`, reglas `E, F, W, I, B, UP, N`.
- **Idioma:** código, docstrings y documentación en español; **identificadores sin tildes**.
- **Commits:** Conventional Commits en español, **asunto sin tildes**.
- **Pruebas:** `uv run pytest` corre con `-q --strict-markers`; la CI añade `-W error`. Un aviso es
  un fallo. La CI corre además con `--all-extras` y **falla si alguna prueba se omite**: una prueba
  nueva que dependa del extra `ml` no puede resolverse con `skipif`.
- **Entorno:** el `.venv` ya está sincronizado con todos los extras; usa `uv run --no-sync`.

---

## Estructura de archivos

| Archivo | Responsabilidad | Tarea |
|---|---|---|
| `ui/paginas/componer.py` | **Nuevo.** Solo `render()`: cabecera, tres tablas, desglose, guardar | 1, 3, 4 |
| `ui/app.py` | Registra la página novena | 1 |
| `tests/unit/test_ui_importable.py` | Añade `ui.paginas.componer` — cierra la meta P8 | 1 |
| `ui/composicion.py` | Gana `FilaReferencia` y `buscar_referencia()` | 2 |
| `tests/unit/test_composicion.py` | Pruebas del buscador | 2 |
| `tests/integration/test_composicion_r6.py` | **Nuevo.** Dos partidas, un equipo, R6 callada | 3 |
| `tests/unit/test_composicion_ia.py` | **Nuevo.** Las cuatro ayudas, con dobles | 4 |

---

## Task 1: La pantalla de composición

**Files:**
- Create: `ui/paginas/componer.py`
- Modify: `ui/app.py` (el bloque `from ui.paginas import (...)` y la lista `paginas`)
- Modify: `tests/unit/test_ui_importable.py` (añadir `"ui.paginas.componer"` a la tupla)

**Interfaces:**
- Consumes, de `ui/composicion.py`: `composicion_desde_tablas(codigo, descripcion, unidad,
  rendimiento, filas_materiales, filas_equipos, filas_mano_obra) -> ComposicionAPU` y
  `ComposicionInvalida(ValueError)`.
- Consumes, de `core.catalog`: `Catalogo`, `abrir_sesion`, `crear_esquema`, `crear_motor`, y de
  `core.catalog.rendimientos`: `proponer_rendimiento(session, codigo_partida) ->
  PropuestaRendimiento | None`, `dispersion_rendimientos(session, codigo_partida) ->
  DispersionRendimiento | None` y `advertencia_rendimiento(dispersion, valor) -> str | None`.
  `PropuestaRendimiento` tiene los campos `rendimiento` (un `Rendimiento` del contrato, con
  `.valor`) y `dispersion`.
- Consumes, de `core.costing`: `calcular_apu(composicion, parametros) -> ResultadoAPU`, y de
  `core.contracts`: `ParametrosCosto`, `Dominio`, `ModalidadManoObra`.
- Produces: la página `ui.paginas.componer` con `TITULO` y `render()`, registrada en `ui/app.py`.

**Contexto que el implementador necesita.** Lee `ui/paginas/actualizacion.py` entero antes de
escribir: es el patrón de esta casa para una página que **escribe** en la base — cómo abre el motor,
cómo enmarca el `try/except (LookupError, ValueError, ArithmeticError, SQLAlchemyError)` y dónde
hace el `commit`. Lee también `ui/paginas/escenarios.py` por su uso de `st.data_editor` y de
`decimal_desde_texto`, y `ui/app.py` por el registro de páginas. El enrutador y las páginas **no
comparten constantes de presentación**: cada página define las suyas, deliberadamente, para no crear
un import circular.

- [ ] **Step 1: Registra la página en la prueba que la vigila (rojo primero)**

En `tests/unit/test_ui_importable.py`, añade `"ui.paginas.componer"` a la tupla, en orden
alfabético (entre `"ui.paginas.catalogo"` y `"ui.paginas.elaborar"`).

- [ ] **Step 2: Corre la prueba y verifica que falla**

```bash
uv run --no-sync pytest tests/unit/test_ui_importable.py -q
```

Esperado: `ModuleNotFoundError: No module named 'ui.paginas.componer'`.

- [ ] **Step 3: Escribe `ui/paginas/componer.py`**

Docstring del módulo: qué caso de uso sirve (UC‑10 crear y UC‑11 corregir, `docs/ERS.md`), y por qué
no contiene lógica — toda vive en `ui/composicion.py`, que es lo único verificable sin Streamlit
(spec §4).

La página, en este orden:

1. **Cabecera de la partida**: `codigo`, `descripcion`, `unidad`. Tres `st.text_input`.
2. **Rendimiento**. El campo se rotula exactamente **«Rendimiento — unidades por día»**. Se precarga
   con `proponer_rendimiento`; si devuelve `None` (menos de dos observaciones) el campo queda vacío
   y se muestra un `st.caption` diciendo que no hay historia suficiente todavía, que es el
   comportamiento correcto y no un error. Si `advertencia_rendimiento` devuelve texto, se muestra
   con `st.warning`: avisa, **no bloquea**.
3. **Condiciones del rendimiento**, `st.text_area`. Es **obligatorio**: mientras esté vacío o solo
   con espacios, el botón de guardar va `disabled=True`. Esto es RF‑33 en la interfaz; el catálogo
   ya lo exige por debajo y lanzaría `ValueError`, pero un botón deshabilitado con su explicación al
   lado es mejor interfaz que una excepción atrapada.
4. **Tres `st.data_editor`** con `num_rows="dynamic"`, uno por tipo de insumo:
   - materiales, con columnas `descripcion`, `unidad`, **`Consumo por unidad`** y `precio`;
   - equipos, con `descripcion`, `cantidad`, `precio`, `depreciacion`;
   - mano de obra, con `descripcion`, `cantidad`, `sueldo` y **`modalidad`**, esta última como
     `st.column_config.SelectboxColumn` con las opciones `jornal` y `destajo`.

   **El rótulo de la columna de materiales es «Consumo por unidad» y el del campo de la partida es
   «Rendimiento — unidades por día». Nunca la misma palabra para las dos cosas** (spec §3.2): la nota
   de campo llama «rendimiento» al consumo de material por unidad de obra y a la producción diaria de
   la cuadrilla, y ahí es exactamente donde se produce el error.

   Al convertir cada `DataFrame` a `list[dict]`, usa la clave interna que espera
   `composicion_desde_tablas` (`cantidad` para materiales, no el rótulo de pantalla). El rótulo es
   presentación; la clave es contrato.

5. **Desglose en vivo**. En cada recarga, construye la composición en memoria con
   `composicion_desde_tablas` y llama a `calcular_apu` con `ParametrosCosto()`. Muestra seis
   `st.metric`: materiales, equipos, mano de obra, costo directo, con administración y precio
   unitario. **No hace falta guardar nada para verlo.** Si `composicion_desde_tablas` lanza
   `ComposicionInvalida`, muestra el mensaje con `st.info` —no `st.error`— y no pinta el desglose:
   mientras se teclea, una tabla a medio llenar es el estado normal, no un fallo.
6. **Guardar**. Busca la partida con `Catalogo.partida()` o la consulta equivalente y decide:
   - si no existe → `cargar_composicion(composicion, lista, dominio, fecha, condiciones)`;
   - si existe → `reemplazar_composicion(composicion, lista, dominio, fecha, condiciones)`.

   Las dos exigen las `condiciones` como quinto argumento. El `commit` lo hace la página, como en
   `ui/paginas/actualizacion.py`. Tras guardar, `st.success` con el código de la partida y el
   precio unitario resultante.

7. Registra la página en `ui/app.py`, en el import y en la lista `paginas`, junto a las otras ocho.

- [ ] **Step 4: Verde y suite completa**

```bash
uv run --no-sync pytest tests/unit/test_ui_importable.py -q
uv run --no-sync pytest -q -W error
uv run --no-sync ruff check .
uv run --no-sync python scripts/meta_prototipo.py --hasta P2
```

Esperado: todo verde y la meta de fase en **8/8**, con P8 en OK. Pega la tabla de la meta en tu
informe.

- [ ] **Step 5: Commit**

```bash
git add ui/paginas/componer.py ui/app.py tests/unit/test_ui_importable.py
git commit -m "feat(ui): pagina de composicion de apu con desglose en vivo"
```

---

## Task 2: El buscador de la referencia MaPreX, como función pura

**Files:**
- Modify: `ui/composicion.py` (añade `FilaReferencia` y `buscar_referencia`)
- Modify: `tests/unit/test_composicion.py` (pruebas nuevas al final)

**Interfaces:**
- Produces: `FilaReferencia` (dataclass inmutable) y
  `buscar_referencia(texto: str, tipo: str, raiz: Path | None = None) -> list[FilaReferencia]`.
  La Tarea 3 lo consume desde la página.

**Los datos, verificados.** Los cuatro archivos están en `data/precios/maprex_2026-07/` y se llaman
`referencia_civil.csv` (37 filas), `referencia_industrial.csv` (13), `referencia_sistemas.csv` (43)
y `referencia_telecom.csv` (18): **111 filas en total**, que es la cifra que declara el spec §3.4.
Sus columnas, en este orden exacto:

```
tipo,insumo,unidad,precio_bs,bono_bs,factor_depreciacion,precio_usd,fecha_vigencia,archivo,ref_maprex,notas
```

`tipo` toma los valores `material`, `equipo` y (donde aplique) el de mano de obra: **compruébalo
leyendo los archivos, no lo supongas**.

**Ruling que no debes revisitar: no hay `bono_usd` y no se inventa.** Ninguno de los cuatro archivos
tiene esa columna, y `lista_maprex_usd.csv` solo lleva `tipo,insumo,unidad,precio`. `FilaReferencia`
carga `bono_bs` tal como está en el archivo. Convertirlo a dólares en la capa de presentación sería
fabricar una cifra que ninguna fuente respalda; si hiciera falta, es trabajo de
`scripts/lista_maprex_usd.py`, que es donde vive la tasa declarada. Anótalo en tu informe.

- [ ] **Step 1: Escribe las pruebas que fallan**

Al final de `tests/unit/test_composicion.py`. Antes de escribirlas, **abre
`data/precios/maprex_2026-07/referencia_civil.csv` y elige una fila real** para el caso positivo:
las pruebas no deben inventar una descripción que no exista. Cubre:

- una búsqueda conocida devuelve la fila esperada, con su `ref_maprex` y su `precio_usd` como
  `Decimal`;
- una búsqueda sin resultados devuelve lista vacía, no `None` ni excepción;
- la búsqueda es insensible a mayúsculas y a acentos (el texto que teclea una persona no coincide
  carácter a carácter con el de un listado técnico);
- `factor_depreciacion` viene lleno solo en filas de equipos y es `None` en las de material;
- todo número es `Decimal` construido desde texto: comprueba el tipo, no solo el valor.

- [ ] **Step 2: Corre las pruebas y verifica que fallan**

```bash
uv run --no-sync pytest tests/unit/test_composicion.py -k referencia -v
```

Esperado: `ImportError` sobre `FilaReferencia` o `buscar_referencia`.

- [ ] **Step 3: Implementa**

```python
@dataclass(frozen=True, slots=True)
class FilaReferencia:
    """Una fila de la referencia MaPreX, como sugerencia editable.

    MaPreX es referencia de mercado, no verdad (spec §3.4): quien presupuesta puede sobrescribir
    el precio con su cotizacion. `factor_depreciacion` solo viene lleno en equipos.
    """

    tipo: str
    descripcion: str
    unidad: str
    precio_usd: Decimal
    factor_depreciacion: Decimal | None
    bono_bs: Decimal | None
    ref_maprex: str
```

`buscar_referencia` lee los cuatro `referencia_*.csv` con el módulo `csv` de la biblioteca estándar,
filtra por coincidencia de subcadena sobre la descripción normalizada y por `tipo`, y devuelve las
filas en el orden en que aparecen. Reutiliza la normalización de texto que ya existe en el
repositorio si la hay —busca en `core/verification/texto.py`— en vez de escribir otra; si la que hay
no sirve para este caso, dilo en el informe y escribe una local, pero no dupliques una que sí sirve.

`ui/composicion.py` sigue sin importar `streamlit` ni `pandas`: usa `csv` y `pathlib`.

- [ ] **Step 4: Verde**

```bash
uv run --no-sync pytest tests/unit/test_composicion.py -q
uv run --no-sync ruff check .
```

- [ ] **Step 5: Commit**

```bash
git add ui/composicion.py tests/unit/test_composicion.py
git commit -m "feat(ui): busqueda en la referencia maprex como funcion pura"
```

---

## Task 3: El buscador en la pantalla, y la regla R6 callada

**Files:**
- Modify: `ui/paginas/componer.py`
- Create: `tests/integration/test_composicion_r6.py`

**Interfaces:**
- Consumes: `buscar_referencia` y `FilaReferencia` de la Tarea 2; la página de la Tarea 1.

**Por qué esta tarea existe, y no es comodidad.** La regla **R6** (`CriterioDepreciacion`) compara el
factor de depreciación de un mismo insumo entre partidas. Dos personas tecleando 0,20 y 0,25 para la
misma retroexcavadora producen un hallazgo de auditoría legítimo y perfectamente evitable. El
autocompletado del factor es lo que lo evita; la prueba de integración es lo que demuestra que lo
evita.

- [ ] **Step 1: Escribe la prueba de integración que falla**

`tests/integration/test_composicion_r6.py`: compón **dos partidas distintas que compartan el mismo
equipo**, tomando el factor de depreciación de la misma `FilaReferencia` en ambas; persístelas con
`cargar_composicion` (con sus condiciones); genera un presupuesto que las incluya y evalúa la regla
R6. **No debe emitir hallazgo.**

Lee `tests/integration/test_persistencia.py` para el fixture `sesion` y el ayudante `_contar`, y
`core/verification/reglas.py` para la firma exacta de `CriterioDepreciacion.evaluar(presupuesto)`.
Mira cómo las pruebas existentes de verificación construyen un `Presupuesto` y reutiliza ese camino
en vez de inventar uno.

Añade el caso negativo en la misma prueba o en una hermana: si las dos partidas llevan factores
distintos para el mismo equipo, **R6 sí emite hallazgo**. Una prueba que solo comprueba el silencio
no distingue «la regla está satisfecha» de «la regla no se está evaluando».

- [ ] **Step 2: Corre y verifica que falla**

```bash
uv run --no-sync pytest tests/integration/test_composicion_r6.py -v
```

- [ ] **Step 3: Cablea el buscador en la página**

Junto a cada una de las tres tablas, un `st.text_input` de búsqueda y un selector con los resultados
de `buscar_referencia(texto, tipo)`. Al elegir una fila se rellena la fila correspondiente de la
tabla: descripción, unidad y precio; **y para equipos, también el factor de depreciación**.

**El precio queda editable.** MaPreX es referencia de mercado, no verdad, y quien presupuesta puede
sobrescribirlo con su cotización (spec §3.4). No lo bloquees ni lo marques como de solo lectura.

Muestra la `ref_maprex` de la fila elegida junto al campo, como `st.caption`: es la procedencia, y
sin ella el número deja de ser trazable.

La lista de precios que se use al guardar declara en su campo `origen` la procedencia y la tasa
declarada de la referencia.

- [ ] **Step 4: Verde y suite completa**

```bash
uv run --no-sync pytest tests/integration/test_composicion_r6.py -v
uv run --no-sync pytest -q -W error
uv run --no-sync ruff check .
```

- [ ] **Step 5: Commit**

```bash
git add ui/paginas/componer.py tests/integration/test_composicion_r6.py
git commit -m "feat(ui): buscador de la referencia maprex con autocompletado de depreciacion"
```

---

## Task 4: Las cuatro ayudas de AREN.IA

**Files:**
- Modify: `ui/paginas/componer.py`
- Create: `tests/unit/test_composicion_ia.py`

**Interfaces disponibles, verificadas.** No las adivines:
- `ml/normalization/normalizador.py`: `NormalizadorPartidas` y `PartidaSimilar`.
- `ml/anomaly/detector.py`: `precios_atipicos(variaciones: Mapping[str, Decimal]) ->
  list[PrecioAtipico]`, `evaluar_rendimiento(...) -> VeredictoRendimiento`, y una constante
  `MINIMO_OBSERVACIONES` que vale 8 porque es un juicio estadístico.
- `ml/prediction/reglas.py`: `predecir_por_reglas(...) -> PrediccionPrecio`,
  `contrastar_aace(...)`, `tecnica_para(registros) -> Tecnica`.
- `core/catalog/rendimientos.py`: `proponer_rendimiento` y `advertencia_rendimiento`, ya cableadas
  en la Tarea 1.

Lee la firma real de cada una antes de llamarla.

**Las cuatro ayudas** (spec §3.7), todas sugerencia y **ninguna bloqueante**:

1. Al escribir la descripción de la partida, ofrecer composiciones de partidas similares del
   catálogo, para partir de algo en vez de una tabla vacía.
2. Al teclear un precio, avisar si es atípico respecto del histórico de ese insumo.
3. El rendimiento propuesto con su dispersión — ya cableado en la Tarea 1; aquí solo se le añade la
   lectura de `ml/anomaly` cuando hay observaciones suficientes.
4. Al terminar la composición, contrastar el precio unitario obtenido contra la estimación por
   reglas, mostrando el marco AACE del resultado.

- [ ] **Step 1: Escribe las pruebas con dobles**

`tests/unit/test_composicion_ia.py`. **Usan dobles, no el modelo real**: el normalizador descarga
pesos de un modelo de lenguaje y una prueba unitaria no puede depender de una descarga.

Lo que hay que probar es **el contrato de la página con las ayudas**, no las ayudas mismas —esas ya
tienen sus pruebas—:

- cuando una ayuda devuelve resultados, la página los ofrece;
- cuando una ayuda **lanza una excepción**, la página sigue funcionando y se puede guardar igual.
  Esta es la prueba que de verdad importa: «no bloqueante» es una promesa que hay que verificar;
- cuando el extra `ml` **no está instalado** (simula el `ImportError`), la página arranca y compone
  sin las ayudas;
- ninguna ayuda modifica la composición por su cuenta: la composición que se guarda es exactamente
  la que la persona compuso.

Extrae a funciones puras en `ui/composicion.py` cualquier lógica que necesites probar sin Streamlit.
Si una ayuda solo se puede probar a través de `render()`, es señal de que hay lógica en el sitio
equivocado.

**Cuidado con la CI:** corre con `--all-extras` y **falla si alguna prueba se omite**. No resuelvas
la dependencia del extra `ml` con `skipif`: simula el `ImportError` con un doble.

- [ ] **Step 2: Corre y verifica que fallan**

```bash
uv run --no-sync pytest tests/unit/test_composicion_ia.py -v
```

- [ ] **Step 3: Cablea las cuatro, con importación perezosa**

Sigue el patrón de `ui/paginas/similares.py`: el import de `ml` ocurre **dentro** de la función que
lo usa, no en la cabecera del módulo, para que la interfaz siga arrancando sin el extra. Cada
llamada va envuelta de modo que un fallo de la ayuda degrade a «sin sugerencia» y nunca impida
guardar.

Ninguna toca `core/`. La página las consulta; ellas no la controlan.

- [ ] **Step 4: Verde, suite completa y el núcleo intacto**

```bash
uv run --no-sync pytest tests/unit/test_composicion_ia.py -v
uv run --no-sync pytest -q -W error
uv run --no-sync ruff check .
git diff p-base --stat -- core/
```

El último comando debe mostrar **exactamente los mismos seis archivos** que ya mostraba al empezar
este plan y ninguno más: `contracts/__init__.py`, `contracts/apu.py`, `costing/motor.py`,
`catalog/repositorio.py`, `catalog/mapeo.py` y `models/entidades.py`. Los seis vienen de las fases
P0‑P1 y de las dos deudas saldadas antes de este plan; **ninguna tarea de este plan toca `core/`**,
así que `git diff <base de tu tarea>..HEAD -- core/` debe salir **vacío**, y ese es el comando que
de verdad prueba lo que aquí importa. Pega la salida de los dos en el informe.

*(Corrección: una versión anterior de este paso decía «cinco archivos» y omitía
`core/contracts/__init__.py`, que introdujo el commit `4ea15a1` de la fase P1. El implementador de
la Tarea 4 lo detectó y lo reportó en vez de silenciarlo o de tocar `core/` para cuadrar la cifra,
que era exactamente la conducta pedida.)*

- [ ] **Step 5: Commit**

```bash
git add ui/paginas/componer.py ui/composicion.py tests/unit/test_composicion_ia.py
git commit -m "feat(ui): ayudas de aprendizaje automatico en la composicion de apu"
```

---

## Cierre de la fase P2

- `uv run --no-sync python scripts/meta_prototipo.py --hasta P2` en **8/8**.
- Meta del sprint en **8/12**.
- La pantalla compone, calcula en vivo, sugiere, guarda y edita; no se puede guardar sin declarar
  rendimiento y condiciones; arranca sin el extra `ml`.
- `git diff p-base --stat -- core/` sin un solo archivo nuevo respecto de P1.

---

## Las fases P3, P4 y P5: hoja de ruta, no tareas

**Por qué no llevan tareas ejecutables aquí.** `PLAN_PROTOTIPO.md` lo declara desde el principio:
cada fase recibe su plan ejecutable **al abrirse**, porque sus tareas dependen de decisiones que se
toman al cerrar la anterior. Escribir hoy los pasos TDD de P4.1 significaría inventar el
comportamiento de `AppTest` sobre una pantalla que todavía no existe. La auditoría de la fase
anterior fue explícita sobre el riesgo contrario: un plan que trae el código de las pruebas escrito
de antemano convierte el paso ROJO del implementador en un trámite, porque una prueba escrita por el
planificador no puede fallar por la razón que el planificador no anticipó.

Lo que sí se declara aquí es la **condición de entrada** de cada fase, lo que debe producir y la
compuerta que la cierra.

### Fase P3 — el flujo completo (2 sesiones)

*Condición de entrada:* P2 cerrada, meta de fase en 8/8.

| Sesión | Debe producir | Cierra |
|---|---|---|
| **P3.1** | De componer a Excel sin salir de la aplicación: presupuesto, auditoría de las siete reglas y exportación. La hoja APU gana columna **Modalidad**. `ui/paginas/elaborar.py` gana el botón de Excel que hoy no tiene | — |
| **P3.2** | Caso de demostración de extremo a extremo y **regresión de la línea base** | meta **P9** y **compuerta GP1** |

**Compuerta GP1**, el momento que define la fase: la regresión debe dar **1 586,61 USD** y
**7 de 7** hallazgos. No seis. Es el indicador 1 de la tesis, y es la única cifra de este sprint que
no admite negociación.

*Riesgo declarado:* `core/budget/excel.py` es el único sitio del núcleo que redondea. La columna
Modalidad es un cambio en `core/`, y por tanto exige el mismo expediente que exigió la modalidad en
el contrato: se documenta antes de escribirse.

### Fase P4 — pruebas (3 sesiones)

*Condición de entrada:* P3 cerrada, GP1 cruzada.

| Sesión | Debe producir | Cierra |
|---|---|---|
| **P4.1** | Las **primeras pruebas automatizadas de interfaz** del repositorio, con `AppTest` de Streamlit, verdes en Linux y en Windows. La matriz requisito → prueba → resultado de `docs/plan_pruebas.md` al día | meta **P10** |
| **P4.2** | `scripts/seed_demo.py` y el guion de prueba manual en `docs/guion_prueba_arenia.md` | — |
| **P4.3** | Corpus simulado determinista, **en cuarentena**: ningún módulo de `ml/` puede referenciarlo | meta **P11** y **compuerta GP2** |

*Riesgo declarado, y es el mayor que queda:* `AppTest` no se ha usado nunca en este repositorio y
tiene que pasar en los dos sistemas operativos de la matriz de la CI. Si resulta inviable, la
degradación es documentar la limitación y reforzar el guion manual de P4.2 — pero eso es una
decisión que se toma **con evidencia**, no por adelantado.

*La cuarentena del corpus simulado no es burocracia:* un corpus sintético que se filtre a `ml/`
convertiría las métricas del módulo predictivo en un artefacto de sus propios datos inventados. La
meta P11 existe para que eso sea imposible de hacer sin querer.

### Fase P5 — cerrar (1 sesión)

*Condición de entrada:* P4 cerrada, GP2 cruzada.

**P5.1** produce el modo entrega, los manuales y la bitácora del sprint, y lleva
`meta_prototipo.py` a **12/12**.

**Detalle que conviene saber ahora:** la meta P12 busca en `docs/bitacora/` un archivo cuyo nombre
contenga la palabra **«prototipo»**. Las bitácoras escritas hasta hoy
(`2026-09-20-P2-deudas-y-composicion.md` y `2026-09-20-P2-hallazgo-migraciones.md`) no la llevan, y
por eso P12 sigue en pendiente — correctamente: esas son bitácoras de sesión y de hallazgo, y la que
P12 busca es la de **cierre del sprint**. Nómbrala en consecuencia.

---

## Lo que este plan deja fuera a propósito

- **Empujar la rama.** Los commits siguen locales por decisión explícita del usuario; el PR #7
  muestra todavía el estado anterior. No se empuja sin que él lo pida.
- **Adoptar una herramienta de migraciones.** Declarado como trabajo futuro en
  `docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md`. Ninguna tarea de este plan cambia el
  esquema, así que no hace falta resolverlo para terminar P2.
- **El asistente de presupuestos con IA** (`PLAN_ASISTENTE.md`, 12 sesiones): planificado y sin
  implementar, y deliberadamente fuera de este sprint.
