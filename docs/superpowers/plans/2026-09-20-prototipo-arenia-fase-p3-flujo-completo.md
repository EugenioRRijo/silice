# AREN.IA — fase P3: el flujo completo, de componer a Excel

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Cerrar el círculo del prototipo: que desde la pantalla de composición se puedan asignar
cantidades, elaborar el presupuesto con su curva, verlo auditado y descargarlo en Excel sin salir de
la aplicación; y demostrar con una prueba de extremo a extremo que el camino nuevo produce
exactamente el mismo resultado que la línea base ya verificada.

**Architecture:** Nada de esto inventa cálculo. `core/budget` y `core/verification` ya elaboran,
encurvan y auditan; la fase P2 dejó la pantalla y las funciones puras. Esta fase **conecta** lo que
existe y añade una sola cosa al núcleo: la columna *Modalidad* en la hoja APU del exportador, que es
donde la decisión D9 se vuelve visible para quien lee el Excel.

**Tech Stack:** Python 3.12 · `Decimal` · Streamlit · openpyxl · SQLAlchemy 2 · pytest · ruff · uv

**Spec:**
[docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md](../specs/2026-09-16-prototipo-composicion-apu-design.md)

**Plan de sesiones:** [PLAN_PROTOTIPO.md](../../../PLAN_PROTOTIPO.md) — este documento desarrolla
las sesiones **P3.1** y **P3.2**.

**Plan anterior:**
[2026-09-20-prototipo-arenia-pantalla-y-fases-restantes.md](2026-09-20-prototipo-arenia-pantalla-y-fases-restantes.md)
— cerró la fase P2 con la pantalla, el buscador y las cuatro ayudas.

## Situación de partida

- Rama `inc/PLAN-prototipo` en `ebe2818`, **17 commits sin empujar**. Árbol limpio.
- Meta del sprint **8/12**; meta de fase `--hasta P2` en **8/8**. Suite: **633 pruebas, 0 omitidas**.
- `ui/paginas/componer.py` compone, busca en MaPreX, autocompleta depreciación, muestra las cuatro
  ayudas y guarda con `cargar_composicion` / `reemplazar_composicion`.
- `git diff p-base --stat -- core/` muestra **seis** archivos, todos de P0‑P1 y de las dos deudas:
  `contracts/__init__.py`, `contracts/apu.py`, `costing/motor.py`, `catalog/repositorio.py`,
  `catalog/mapeo.py`, `models/entidades.py`. La Tarea 1 de este plan añadirá `budget/excel.py`.

## Global Constraints

- **`Decimal` en todo lo monetario y dimensional.** Nunca `float`. Se construye desde texto.
- **`core/budget/excel.py` es el único sitio del sistema que redondea a dos decimales.** Ninguna
  otra tarea de este plan redondea, y esa no lo cambia: usa el `_redondear` que ya existe allí.
- **`tests/unit/test_costing.py` y `tests/fixtures/apu_linea_base.py` NO se modifican.** Tampoco
  `tests/fixtures/presupuesto_auditado.py` ni `tests/integration/test_auditoria_7_de_7.py`: son la
  prueba de aceptación crítica del indicador 1 y esta fase no los toca.
- **`core/contracts/` no se toca.** Está declarado estable por `CLAUDE.md` §5.
- **Solo la Tarea 1 toca `core/`**, y su commit **no puede tocar `adapters/` ni `ml/`**
  (`scripts/guardia_nucleo.py`). Puede tocar `tests/`, que no cuenta.
- **`ui/composicion.py` no importa `streamlit` ni `pandas`**, ni dentro de una función (meta P7).
- **Toda sesión que añada o cambie una columna del esquema declara antes qué pasa con las bases ya
  creadas** (`docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md`). **Ninguna tarea de este plan
  cambia el esquema de la base**: la columna de la Tarea 1 es de una hoja de Excel, no de SQLite.
  Si alguna tarea parece necesitar un cambio de esquema, para y reporta.
- ruff: `line-length = 100`, `target-version = "py312"`, reglas `E, F, W, I, B, UP, N`.
- **Idioma:** código, docstrings y documentación en español; **identificadores sin tildes**.
- **Commits:** Conventional Commits en español, **asunto sin tildes**.
- **Pruebas:** `uv run pytest -q --strict-markers`; la CI añade `-W error` y corre con
  `--all-extras`, y **falla si alguna prueba se omite**: nada de `skipif`.
- **Entorno:** el `.venv` ya está sincronizado; usa `uv run --no-sync`.

---

## Estructura de archivos

| Archivo | Responsabilidad | Tarea |
|---|---|---|
| `core/budget/excel.py` | La tabla de mano de obra de la hoja APU gana *Modalidad* | 1 |
| `tests/unit/test_budget.py` | La prueba de las cuatro hojas comprueba la columna nueva | 1 |
| `ui/paginas/componer.py` | Cantidades, elaborar, informe auditado y descarga | 2 |
| `ui/paginas/elaborar.py` | Gana el botón de Excel que hoy no tiene | 2 |
| `tests/integration/test_composicion_extremo_a_extremo.py` | **Nuevo.** Regresión y demostración | 3 |
| `scripts/seed_demo.py` | **Nuevo.** Deja la demostración cargada en la base | 4 |

---

## Task 1: La modalidad, visible en el Excel

**Files:**
- Modify: `core/budget/excel.py` (función `_bloque_apu`, el encabezado y las filas de mano de obra)
- Modify: `tests/unit/test_budget.py` (la prueba `test_exportar_excel_escribe_cuatro_hojas`, y una
  aserción nueva sobre la columna)

**Interfaces:**
- Consumes: `LineaManoObra.modalidad`, un `ModalidadManoObra` (`StrEnum` con `JORNAL = "jornal"` y
  `DESTAJO = "destajo"`), que existe desde la fase P1.
- Produces: nada que otra tarea consuma en código; la Tarea 3 comprobará la hoja resultante.

**Por qué esta columna importa y no es decoración.** La decisión **D9** distingue el jornal del
destajo (artículo 114 de la LOTTT): bajo destajo el campo `sueldo` **no es un sueldo diario sino el
precio por unidad de partida**, entra completo al precio unitario y no recibe ni el factor de
prestaciones ni el bono. Un Excel que muestra «Sueldo: 6,00» sin decir bajo qué modalidad invita
exactamente al malentendido que D9 existe para evitar. Quien audite el libro tiene que poder verlo.

**El estado actual, verificado.** `_bloque_apu` escribe hoy:

```python
    _encabezado(hoja, ["Mano de obra", "Obreros", "Sueldo", "Total"])
    for obrero in apu.mano_obra:
        hoja.append([
            obrero.descripcion,
            _redondear(obrero.cantidad),
            _redondear(obrero.sueldo),
            _redondear(obrero.total),
        ])
```

Las otras dos tablas del bloque (materiales y equipos) tienen cinco columnas; esta tiene cuatro.

- [ ] **Step 1: Escribe la prueba que falla**

En `tests/unit/test_budget.py`, junto a `test_exportar_excel_escribe_cuatro_hojas` (está alrededor
de la línea 194 — léela entera antes de tocar nada, y sigue su forma de abrir el libro).

Una prueba nueva que exporte un presupuesto cuyo APU tenga **dos líneas de mano de obra, una en
cada modalidad**, y comprobe sobre la hoja `APU`:

- que el encabezado de la tabla de mano de obra contiene la palabra `Modalidad`;
- que la fila del obrero a jornal muestra `jornal` y la del destajista muestra `destajo`;
- que la columna del total sigue siendo la última de la fila.

No transcribas montos de la línea base: construye un APU pequeño para la prueba, o reutiliza el que
la prueba vecina ya use. Si `tests/unit/test_budget.py` tiene un ayudante para construir
presupuestos de prueba, úsalo en vez de escribir otro.

- [ ] **Step 2: Corre la prueba y verifica que falla**

```bash
uv run --no-sync pytest tests/unit/test_budget.py -k modalidad -v
```

Esperado: falla porque el encabezado no contiene `Modalidad`.

- [ ] **Step 3: Implementa**

En `_bloque_apu`, el encabezado pasa a cinco títulos y la fila a cinco valores, con la modalidad
**antes del total**, para que el total siga siendo la última columna como en las otras dos tablas:

```python
    _encabezado(hoja, ["Mano de obra", "Obreros", "Sueldo", "Modalidad", "Total"])
    for obrero in apu.mano_obra:
        hoja.append([
            obrero.descripcion,
            _redondear(obrero.cantidad),
            _redondear(obrero.sueldo),
            obrero.modalidad.value,
            _redondear(obrero.total),
        ])
```

`obrero.modalidad` es un `StrEnum`: escribe `.value` para que openpyxl guarde el texto y no la
representación del enum.

Amplía el docstring del módulo o de `_bloque_apu` con una línea que diga por qué está la columna:
bajo destajo, `sueldo` es precio por unidad de partida y no un sueldo diario (decisión D9).

- [ ] **Step 4: Verde, y la guardia del núcleo**

```bash
uv run --no-sync pytest tests/unit/test_budget.py -q
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
```

- [ ] **Step 5: Commit**

Este commit toca `core/`. **No añadas nada de `adapters/` ni de `ml/`.**

```bash
git add core/budget/excel.py tests/unit/test_budget.py
git commit -m "feat(budget): la hoja apu muestra la modalidad de mano de obra"
```

Después comprueba que la guardia pasa sobre tu propio commit:

```bash
uv run --no-sync python scripts/guardia_nucleo.py --base HEAD~1
```

---

## Task 2: De componer a Excel sin salir de la aplicación

**Files:**
- Modify: `ui/paginas/componer.py`
- Modify: `ui/paginas/elaborar.py`

**Interfaces disponibles, verificadas. No las adivines:**
- `core.budget.elaborar(items, composiciones, parametros, codigo, fecha, moneda=..., plan=None) -> ResultadoElaboracion`
  — genera el presupuesto, le añade la curva si hay plan **y lo audita siempre**.
- `core.budget.plan_secuencial(presupuesto, formato=FORMATO_PERIODO) -> list[PeriodoPlan]`.
- `core.budget.exportar_excel(presupuesto, informe, ruta) -> Path`.
- `core.verification.informe.auditar(presupuesto, reglas=REGLAS) -> InformeAuditoria`, e
  `InformeAuditoria.a_markdown() -> str`, más `.cumple`, `.por_severidad()` y `.por_regla()`.
- De `ui/composicion.py`: `item_desde_cantidad(codigo, descripcion, unidad, cantidad, origen_id, dominio) -> ItemComputo`.

Lee `core/budget/presupuesto.py:67` para la firma exacta de `elaborar` y qué trae
`ResultadoElaboracion` antes de usarlo.

**Por qué `plan_secuencial` y no ningún plan.** Sin plan, el presupuesto no lleva curva y **R2 lo
hace constar**; con plan, la curva cierra exactamente en el total y R2 y R7 quedan limpias. El
prototipo debe enseñar un presupuesto sano, no uno que dispara dos reglas por omisión. Es lo que ya
hace `ui/paginas/elaborar.py`: léelo.

- [ ] **Step 1: Las cantidades de obra, en la pantalla de composición**

Tras la sección de guardar, una sección nueva: una tabla donde asignar **cantidad de obra** a las
partidas ya guardadas, con su `origen_id` — que es obligatorio, porque una cantidad sin origen no es
trazable y el sistema la trata como hallazgo, no como dato.

Cada fila produce un `ItemComputo` con `item_desde_cantidad(...)`, con el `dominio` que ya declara
la cabecera de la partida.

- [ ] **Step 2: Elaborar y auditar**

Un botón elabora: construye el presupuesto con `elaborar(...)`, pasándole
`plan=plan_secuencial(borrador)` como hace `elaborar.py`, y muestra:

- los totales del presupuesto;
- **el informe de auditoría con `a_markdown()`**, dentro de un `st.markdown`. Se muestra siempre,
  tenga hallazgos o no: el informe de auditoría se genera siempre, sin que el usuario lo pida, y eso
  es principio del proyecto, no preferencia de pantalla.
- un resumen por severidad con `por_severidad()`, para que la persona vea de un vistazo si algo
  grave saltó.

- [ ] **Step 3: La descarga**

`exportar_excel(...)` escribe a una ruta. Escríbela en un archivo temporal, léela en memoria y
ofrécela con `st.download_button`, **copiando el patrón que `ui/paginas/actualizacion.py` ya usa
para descargar**: léelo y haz lo mismo, con el mismo tipo MIME y la misma forma de nombrar el
archivo. No inventes un patrón nuevo para algo que la casa ya resolvió.

- [ ] **Step 4: El botón que le falta a `elaborar.py`**

`ui/paginas/elaborar.py` elabora presupuestos y **no tiene botón de Excel**. Añádeselo, con el mismo
patrón del paso anterior. Es media docena de líneas y cierra una asimetría que hoy no tiene
justificación.

- [ ] **Step 5: Verde y ejecución real**

```bash
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
```

Y **ejecuta la pantalla**: un script desechable de dos líneas que importe `render` de
`ui.paginas.componer` y lo llame, conducido con `AppTest.from_file(...)`. Reporta los widgets y la
lista de excepciones. **`AppTest.from_function` no sirve para estas páginas**: serializa el código
de la función y pierde los globales del módulo, fallando con `NameError`. Borra los archivos
desechables después; las pruebas de interfaz de verdad son la sesión P4.1.

- [ ] **Step 6: Commit**

```bash
git add ui/paginas/componer.py ui/paginas/elaborar.py
git commit -m "feat(ui): presupuesto auditado y exportacion desde la composicion"
```

---

## Task 3: La regresión de extremo a extremo — compuerta GP1

**Files:**
- Create: `tests/integration/test_composicion_extremo_a_extremo.py`

**Interfaces:**
- Consumes: `ui.composicion.composicion_desde_tablas`, el fixture `tests/fixtures/apu_linea_base.py`
  (**solo lectura**) y `tests/fixtures/presupuesto_auditado.py` (**solo lectura**).
- Produces: la meta **P9** y la compuerta **GP1**.

**Lo que ya existe, y que NO debes duplicar.** Compruébalo antes de escribir una línea:

- `tests/integration/test_auditoria_7_de_7.py` **ya es** la prueba de aceptación crítica del
  indicador 1: afirma que las siete inconsistencias esperadas se detectan, `len(esperadas) == 7` y
  `len(esperadas & detectadas) == 7`.
- `tests/fixtures/presupuesto_auditado.py` **ya contiene** el presupuesto con las siete
  inconsistencias, y su docstring dice explícitamente que no repite ningún dato de la línea base.
- `tests/fixtures/apu_linea_base.py` **ya declara** `TOTAL_PRESUPUESTO_AUDITADO = Decimal("1586.61")`.
- `tests/integration/test_presupuesto_linea_base.py` **ya prueba**
  `test_elaborar_desde_el_catalogo_reproduce_1586_61`.

**Entonces, ¿qué aporta esta prueba que no exista?** Una sola cosa, y es la que cierra la fase:
**que el camino nuevo —el de la pantalla— llega al mismo sitio que el camino viejo.** Hasta ahora,
los 1 586,61 y el 7 de 7 se demuestran elaborando desde el catálogo. Esta prueba los demuestra
**componiendo con `composicion_desde_tablas`**, que es lo que hace la persona cuando teclea en la
pantalla. Si las dos rutas divergen, el prototipo miente.

- [ ] **Step 1: La prueba de regresión**

Para cada uno de los cinco APU de la línea base: toma sus líneas **del fixture**, conviértelas a las
listas de diccionarios de texto que `composicion_desde_tablas` espera, y compón. Afirma que la
`ComposicionAPU` resultante **es igual** a la del fixture — igualdad de dataclass, que es como el
repositorio compara ya en `tests/integration/test_persistencia.py`.

Después elabora el presupuesto con esas composiciones y afirma el total contra
`TOTAL_PRESUPUESTO_AUDITADO`, **importado del fixture**: no escribas `1586.61` en el archivo.

**No transcribas ni un número.** Si te encuentras tecleando una cantidad, un precio o una
descripción, estás haciendo la prueba mal: todo sale del fixture.

- [ ] **Step 2: Corre y verifica que falla**

```bash
uv run --no-sync pytest tests/integration/test_composicion_extremo_a_extremo.py -v
```

- [ ] **Step 3: La prueba de demostración**

En el mismo archivo, un presupuesto construido para la demostración —**que no proviene de obra
ejecutada, y su docstring debe decirlo**— que ejercite:

- jornal y destajo **en la misma partida**;
- materiales con desperdicio;
- equipos con depreciación;
- la curva, con `plan_secuencial`;
- y la exportación: que `exportar_excel` escriba las cuatro hojas y que la de APU muestre la columna
  *Modalidad* que añadió la Tarea 1.

- [ ] **Step 4: Verde, y la compuerta**

```bash
uv run --no-sync pytest tests/integration/test_composicion_extremo_a_extremo.py -v
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
uv run --no-sync python scripts/meta_prototipo.py --hasta P3
```

**Compuerta GP1:** la regresión da **1 586,61 USD** y la auditoría **7 de 7**; la demostración
ejercita las dos modalidades; la meta `--hasta P3` en OK. Pega la tabla de la meta en tu informe.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_composicion_extremo_a_extremo.py
git commit -m "test(integration): composicion de extremo a extremo y regresion de la linea base"
```

---

## Task 4: La demostración, sembrada en la base

**Files:**
- Create: `scripts/seed_demo.py`

**Interfaces:**
- Consumes: la composición de demostración de la Tarea 3 — **si esa prueba la construye con una
  función reutilizable, impórtala en vez de copiarla**; si no, extrae la construcción a un sitio
  único y que ambas lo usen. Un caso de demostración escrito dos veces es dos casos que divergen.
- Consumes: `Catalogo.cargar_composicion(composicion, lista, dominio, fecha, condiciones)` — las
  `condiciones` son obligatorias (RF‑33).

- [ ] **Step 1: Escribe el script**

Sigue el patrón de `scripts/seed.py` y de los otros tres sembradores: acepta `--db`, es idempotente
o lo declara, y no escribe sobre `data/apu.db` por accidente.

**Su docstring debe declarar que es un caso didáctico y no una obra ejecutada.** Esto no es formalidad:
`scripts/meta_datos.py` vigila que ningún documento del repositorio afirme que un dato ficticio es
real, y el proyecto tiene una bitácora entera dedicada a esa limpieza.

Las condiciones del rendimiento que declare deben decir, como las de los otros sembradores, que el
rendimiento **no proviene de una ejecución medida**.

- [ ] **Step 2: Córrelo de verdad, contra una base temporal**

```bash
TMP=$(uv run --no-sync python -c "import tempfile;print(tempfile.gettempdir())")
uv run --no-sync python scripts/seed_demo.py --db "$TMP/demo.db"
```

Reporta la orden exacta y su salida. **Nunca contra `data/apu.db`.**

- [ ] **Step 3: Verde y metas**

```bash
uv run --no-sync pytest -q -W error --strict-markers
uv run --no-sync ruff check .
uv run --no-sync python scripts/meta_datos.py
uv run --no-sync python scripts/meta_prototipo.py --hasta P3
```

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_demo.py
git commit -m "feat(scripts): siembra del caso de demostracion de arenia"
```

---

## Cierre de la fase P3

- Meta `--hasta P3` en **OK**; meta del sprint en **9/12**.
- **Compuerta GP1 cruzada**: 1 586,61 USD y 7 de 7, por el camino de la pantalla.
- `git diff p-base --stat -- core/` muestra **siete** archivos: los seis de antes más
  `budget/excel.py`. Ninguno más.
- De componer a Excel sin salir de la aplicación, con el informe de auditoría siempre a la vista.

Las fases P4 y P5 reciben su propio plan, con las condiciones de entrada que ya declara el plan
anterior en su hoja de ruta.
