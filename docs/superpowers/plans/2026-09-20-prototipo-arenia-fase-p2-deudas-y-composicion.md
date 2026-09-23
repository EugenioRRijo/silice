# AREN.IA — fase P2, deudas del ramal y funciones puras de composición: plan de implementación

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Saldar las dos deudas que la revisión final de las fases P0–P1 dejó declaradas —la
modalidad de mano de obra no se persiste y RF‑33 solo se exige en la mitad de los caminos— y dejar
escritas las funciones puras que convierten las tablas de la pantalla en un `ComposicionAPU`
(Sesión P2.1 de `PLAN_PROTOTIPO.md`).

**Architecture:** Las dos deudas viven en la misma capa, el catálogo: una columna nueva en
`models.ComposicionAPU` y un campo en `LineaCatalogo` bastan para que la modalidad dé la vuelta por
SQLite sin perderse, y un parámetro obligatorio en `cargar_composicion` cierra el camino de UC‑10
igual que `reemplazar_composicion` cerró el de UC‑11. La tercera tarea es documental: el spec §4
omite los dos archivos del catálogo que ambas deudas tocan. La cuarta abre P2 propiamente:
`ui/composicion.py`, funciones puras sin Streamlit, que es lo único verificable antes de que exista
una prueba de interfaz.

**Tech Stack:** Python 3.12 · `Decimal` · SQLAlchemy 2 · pytest · ruff · uv

**Spec:**
[docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md](../specs/2026-09-16-prototipo-composicion-apu-design.md)

**Plan de sesiones:** [PLAN_PROTOTIPO.md](../../../PLAN_PROTOTIPO.md) — este documento desarrolla
las dos deudas declaradas al cerrar P1 y la Sesión **P2.1**. Las sesiones P2.2, P2.3 y P2.4 reciben
su propio plan: dependen de lo que esta sesión deje escrito.

**Deudas que se saldan** (declaradas en el ledger del ramal anterior, revisión final):

1. La modalidad no se persiste. `core/catalog/mapeo.py:81` construye `LineaManoObra` con tres
   posicionales y `models.ComposicionAPU` no tiene columna: una línea a destajo que dé la vuelta
   por el catálogo **vuelve como jornal**. → Tarea 1.
2. RF‑33 cumplido a medias. `reemplazar_composicion` exige condiciones y lanza `ValueError`;
   `cargar_composicion` —el camino de UC‑10, crear una partida nueva— todavía no. → Tarea 2.
3. El spec §4 no lista `core/models/entidades.py` ni `core/catalog/mapeo.py` entre los archivos que
   se tocan, y las dos tareas anteriores los tocan. → Tarea 3.

## Global Constraints

- **`Decimal` en todo lo monetario y dimensional.** Nunca `float` en cantidades, precios, factores
  ni rendimientos. Se construye siempre desde texto: `Decimal("6")`, nunca `Decimal(6.0)`.
- **Se redondea solo al presentar**, a dos decimales. Ninguna tarea de este plan redondea.
- **`tests/unit/test_costing.py` y `tests/fixtures/apu_linea_base.py` NO se modifican.** Si una
  tarea parece exigirlo, la tarea está mal: detente y reporta.
- **Los cinco APU de la línea base no cambian de precio.** `uv run python scripts/meta_prototipo.py
  --hasta P1` debe seguir dando 6/6 al terminar cada tarea.
- **Ningún commit que toque `core/` puede tocar `adapters/` ni `ml/`** en el mismo commit
  (`scripts/guardia_nucleo.py`).
- **`ui/composicion.py` no importa `streamlit`** —ni al principio del módulo ni dentro de una
  función—. Es la meta P7 del sprint y se comprueba por texto.
- **`core/` no importa `ui/`, `adapters/`, `ml/` ni `api/`** (`tests/unit/test_arquitectura.py`).
- **ruff:** `line-length = 100`, `target-version = "py312"`, reglas `E, F, W, I, B, UP, N`.
- **Idioma:** código, docstrings y documentación en español; **identificadores sin tildes**.
- **Commits:** Conventional Commits en español, **asunto sin tildes**.
- **Pruebas:** `uv run pytest` corre con `-q --strict-markers`; la CI añade `-W error`. Un aviso es
  un fallo.
- **Entorno:** `uv sync`. El extra `ui` no hace falta: la Tarea 4 no importa Streamlit.

---

## Estructura de archivos

| Archivo | Responsabilidad | Tarea |
|---|---|---|
| `core/models/entidades.py` | Columna `modalidad` en la línea de composición persistida | 1 |
| `core/catalog/mapeo.py` | `LineaCatalogo.modalidad`; ida y vuelta contrato ↔ modelo | 1, 2 |
| `tests/integration/test_persistencia.py` | La modalidad sobrevive el viaje por SQLite | 1, 2 |
| `core/catalog/repositorio.py` | `cargar_composicion` exige las condiciones (RF‑33) | 2 |
| `scripts/seed.py` | Declara las condiciones al cargar, no después | 2 |
| `scripts/seed_industrial.py`, `seed_sistemas.py`, `seed_telecom.py` | Declaran sus condiciones | 2 |
| `scripts/medir_rnf03.py` | Declara las condiciones de su carga sintética | 2 |
| `docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md` | §4 nombra los dos archivos del catálogo; §3.3 cita el camino de UC‑10 | 3 |
| `docs/ERS.md` | RF‑33 dice explícitamente que alcanza a los dos caminos | 3 |
| `ui/composicion.py` | **Nuevo.** Tablas → `ComposicionAPU`; cantidad → `ItemComputo`; `Decimal` desde texto | 4 |
| `ui/paginas/escenarios.py` | Importa el conversor compartido en vez de tener el suyo | 4 |
| `tests/unit/test_composicion.py` | **Nuevo.** Las pruebas de las funciones puras | 4 |

---

## Task 1: La modalidad viaja por el catálogo

**Files:**
- Modify: `core/models/entidades.py:99-113` (clase `ComposicionAPU`, la persistida)
- Modify: `core/catalog/mapeo.py:81` (`a_composicion`), `:113-127` (`LineaCatalogo`),
  `:158-167` (`lineas_de`), `:196-214` (`a_modelo_lineas`)
- Test: `tests/integration/test_persistencia.py` (dos pruebas nuevas al final del archivo)

**Interfaces:**
- Consumes: `core.contracts.apu.ModalidadManoObra` (`JORNAL = "jornal"`, `DESTAJO = "destajo"`,
  es un `StrEnum`) y `LineaManoObra(descripcion, cantidad, sueldo, modalidad=JORNAL)`, ambos ya
  existentes desde la fase P1.
- Produces: `models.ComposicionAPU.modalidad: str | None` y
  `mapeo.LineaCatalogo.modalidad: ModalidadManoObra | None`. La Tarea 2 toca el mismo
  `mapeo.py` pero otra función (`a_modelo_rendimiento_estimado`); no hay solape de líneas.

**Contexto que el implementador necesita:** `core/models/base.py:8` declara
`class Base(DeclarativeBase)` — **no** es `MappedAsDataclass`, así que una columna con `default=`
puede ir en cualquier posición de la clase. El esquema se crea con `Base.metadata.create_all`
(`core/catalog/sesion.py:32`); no hay Alembic y **no hay ninguna base SQLite versionada en git**
(`data/apu.db` se genera con `scripts/seed.py`), de modo que la columna nueva no necesita
migración. La columna es anulable por la misma razón que `depreciacion`: solo las líneas de un tipo
de insumo la llevan.

- [ ] **Step 1: Escribe las dos pruebas que fallan**

Al final de `tests/integration/test_persistencia.py`:

```python
def test_la_modalidad_a_destajo_sobrevive_el_viaje_por_el_catalogo(sesion):
    """Deuda 1 del ramal: una línea a destajo volvía como jornal (mapeo.py construía tres campos).

    Es la diferencia entre 6,00 USD/m2 y 6,00 × (1 + FCAS) + bono, dividido entre el rendimiento:
    el destajo del artículo 114 de la LOTTT deja de serlo en cuanto se guarda.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    mixto = contracts.ComposicionAPU(
        codigo_partida="LB-99-MIX",
        descripcion="Partida de prueba con las dos modalidades",
        unidad="m2",
        rendimiento=Decimal("20"),
        mano_obra=(
            contracts.LineaManoObra("Obrero de primera", Decimal("1"), Decimal("12.50")),
            contracts.LineaManoObra(
                "Friso a destajo",
                Decimal("1"),
                Decimal("6.00"),
                contracts.ModalidadManoObra.DESTAJO,
            ),
        ),
    )

    catalogo.cargar_composicion(
        mixto, lista, contracts.Dominio.CIVIL, linea_base.FECHA_LINEA_BASE
    )
    sesion.flush()
    vuelta = Catalogo(sesion).composicion("LB-99-MIX", fecha=linea_base.FECHA_LINEA_BASE)

    modalidades = [linea.modalidad for linea in vuelta.mano_obra]
    assert modalidades == [
        contracts.ModalidadManoObra.JORNAL,
        contracts.ModalidadManoObra.DESTAJO,
    ]
    assert vuelta.total_obreros == Decimal("1"), "el destajista no devenga bono de alimentación"


def test_una_linea_sin_modalidad_persistida_vuelve_como_jornal(sesion):
    """Las filas escritas antes de la columna tienen NULL: el contrato las lee como JORNAL.

    Es el valor por defecto del contrato y el de toda la línea base, así que la lectura de una
    base anterior a esta columna no cambia ni un céntimo.
    """
    linea = sesion.scalars(
        select(models.ComposicionAPU)
        .join(models.Insumo)
        .where(models.Insumo.tipo == models.TipoInsumo.MANO_OBRA)
    ).first()
    linea.modalidad = None
    sesion.flush()

    vuelta = Catalogo(sesion).composicion(linea.partida.codigo)

    assert all(
        obrero.modalidad is contracts.ModalidadManoObra.JORNAL for obrero in vuelta.mano_obra
    )
```

Comprueba antes de escribirlas que `contracts.ComposicionAPU`, `contracts.LineaManoObra`,
`contracts.ModalidadManoObra` y `contracts.Dominio` se exporten desde `core.contracts` (el archivo
ya importa `from core import contracts, models`); si alguno no está reexportado, impórtalo de
`core.contracts.apu` en vez de reexportarlo —**no** toques `core/contracts/__init__.py`.

- [ ] **Step 2: Corre las pruebas y verifica que fallan**

```bash
uv run pytest tests/integration/test_persistencia.py -k modalidad -v
```

Esperado: la primera falla con `AssertionError` porque las dos modalidades vuelven como `JORNAL`;
la segunda falla con `AttributeError`/`TypeError` porque `models.ComposicionAPU` no tiene
`modalidad`.

- [ ] **Step 3: Añade la columna al modelo persistido**

En `core/models/entidades.py`, dentro de `class ComposicionAPU(Base)`, justo después de
`depreciacion`:

```python
    modalidad: Mapped[str | None] = mapped_column(String(10), default=None)
```

y amplía el docstring de la clase con una línea que diga por qué es anulable: `depreciacion` solo
la llevan los equipos y `modalidad` solo la mano de obra; `NULL` en una línea de mano de obra se
lee como `jornal`, que es el valor por defecto del contrato.

- [ ] **Step 4: Lleva la modalidad por el aplanado del catálogo**

En `core/catalog/mapeo.py`:

1. Importa `ModalidadManoObra` junto a los otros tipos del contrato que ya importa el módulo.
2. `LineaCatalogo` gana un último campo con valor por defecto:

```python
    modalidad: ModalidadManoObra | None = None
```

   con una línea en el docstring: solo las líneas de mano de obra la llevan, igual que
   `depreciacion` solo la llevan los equipos.

3. En `lineas_de`, el bloque de mano de obra pasa `modalidad=obrero.modalidad`.
4. En `a_modelo_lineas`, la línea persistida gana:

```python
            modalidad=linea.modalidad.value if linea.modalidad is not None else None,
```

5. En `a_composicion`, la rama de mano de obra deja de construir con tres posicionales:

```python
            mano_obra.append(
                LineaManoObra(
                    insumo.descripcion,
                    linea.cantidad,
                    precio,
                    ModalidadManoObra(linea.modalidad)
                    if linea.modalidad
                    else ModalidadManoObra.JORNAL,
                )
            )
```

- [ ] **Step 5: Corre las pruebas nuevas y luego la suite entera**

```bash
uv run pytest tests/integration/test_persistencia.py -k modalidad -v
uv run pytest -q
uv run ruff check .
uv run python scripts/meta_prototipo.py --hasta P1
```

Esperado: las dos nuevas en verde, la suite entera en verde, ruff limpio y la meta en 6/6.

- [ ] **Step 6: Commit**

```bash
git add core/models/entidades.py core/catalog/mapeo.py tests/integration/test_persistencia.py
git commit -m "fix(catalog): persiste la modalidad de mano de obra por linea"
```

---

## Task 2: RF‑33 completo — `cargar_composicion` exige las condiciones

**Files:**
- Modify: `core/catalog/repositorio.py:138-169` (`cargar_composicion`)
- Modify: `core/catalog/mapeo.py:233-255` (`a_modelo_rendimiento_estimado`)
- Modify: `scripts/seed.py:96-108`
- Modify: `scripts/seed_industrial.py:153`, `scripts/seed_sistemas.py:143`,
  `scripts/seed_telecom.py:464`, `scripts/medir_rnf03.py:66`
- Test: `tests/integration/test_persistencia.py` (una prueba nueva; y hay que actualizar la llamada
  de `test_cargar_composicion_dos_veces_lanza_valueerror:251` y la de la Tarea 1)

**Interfaces:**
- Consumes: `Catalogo.reemplazar_composicion(composicion, lista, dominio, fecha_rendimiento,
  condiciones)` — la firma que esta tarea replica.
- Produces: `Catalogo.cargar_composicion(composicion, lista, dominio, fecha_rendimiento,
  condiciones)` con `condiciones: str` **obligatorio**, y
  `a_modelo_rendimiento_estimado(composicion, partida, fecha, condiciones)` sin valor por defecto.

**Por qué es una deuda y no una preferencia.** El spec §3.3 es la autoridad vinculante y dice, en
negrita: «el sistema **no persiste una composición cuyo rendimiento no haya sido declarado
explícitamente junto con sus condiciones.** No hay valor por defecto que pase en silencio». Hoy
`a_modelo_rendimiento_estimado` tiene `condiciones: str = ""` y su docstring argumenta que
`cargar_composicion` las declara «por fuera». `scripts/seed.py` lo hace así de verdad —carga, busca
el `Rendimiento` recién creado y le asigna las condiciones—, pero los otros tres sembradores
(`seed_industrial`, `seed_sistemas`, `seed_telecom`) y `medir_rnf03` **no las declaran en absoluto**:
dejan `condiciones=''` en la base. Cuando la pantalla de UC‑10 llame a `cargar_composicion` en P2.2,
heredará ese silencio. El parámetro obligatorio es lo que lo hace imposible.

- [ ] **Step 1: Escribe la prueba que falla**

En `tests/integration/test_persistencia.py`, junto a las otras de carga:

```python
def test_cargar_composicion_sin_condiciones_lanza_valueerror(sesion):
    """RF‑33 alcanza los dos caminos, no solo el de UC‑11 (spec §3.3).

    `reemplazar_composicion` ya lo exigía; crear una partida nueva sin declarar en qué condiciones
    se midió su rendimiento dejaba un ESTIMADO con `condiciones=''`, que es exactamente el valor
    por defecto silencioso que el spec prohíbe.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    nueva = replace(linea_base.APU_RELLENO, codigo_partida="LB-98-NUE")
    lineas_antes = _contar(sesion, models.ComposicionAPU)

    with pytest.raises(ValueError, match="RF-33"):
        catalogo.cargar_composicion(
            nueva, lista, contracts.Dominio.CIVIL, linea_base.FECHA_LINEA_BASE, "   "
        )

    assert _contar(sesion, models.ComposicionAPU) == lineas_antes


def test_cargar_composicion_registra_las_condiciones_declaradas(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    nueva = replace(linea_base.APU_RELLENO, codigo_partida="LB-97-NUE")

    catalogo.cargar_composicion(
        nueva,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        "cuadrilla de cuatro, suelo seco",
    )
    sesion.flush()

    registrado = sesion.scalars(
        select(models.Rendimiento)
        .join(models.Partida)
        .where(models.Partida.codigo == "LB-97-NUE")
    ).one()
    assert registrado.condiciones == "cuadrilla de cuatro, suelo seco"
    assert registrado.tipo == contracts.TipoRendimiento.ESTIMADO
```

Si `contracts.TipoRendimiento` no está reexportado, compara contra la cadena `"estimado"` y
explica por qué en un comentario de una línea.

- [ ] **Step 2: Corre la prueba y verifica que falla**

```bash
uv run pytest tests/integration/test_persistencia.py -k "condiciones" -v
```

Esperado: la primera falla con `TypeError` (la firma solo acepta cuatro argumentos).

- [ ] **Step 3: Exige las condiciones en `cargar_composicion`**

En `core/catalog/repositorio.py`, la firma pasa a:

```python
    def cargar_composicion(
        self,
        composicion: ComposicionAPU,
        lista: models.ListaPrecios,
        dominio: Dominio,
        fecha_rendimiento: date,
        condiciones: str,
    ) -> ResumenCarga:
```

y lo primero del cuerpo, antes de buscar la partida, es la guarda —el orden importa: rechazar antes
de crear nada deja la sesión sin partida huérfana:

```python
        if not condiciones.strip():
            raise ValueError(
                "cargar_composicion exige las condiciones del rendimiento (RF-33): el sistema no "
                "persiste una composición cuyo rendimiento no se declare junto con ellas"
            )
```

El `add` del rendimiento pasa las condiciones:

```python
        self._sesion.add(
            a_modelo_rendimiento_estimado(composicion, partida, fecha_rendimiento, condiciones)
        )
```

Reescribe el párrafo del docstring que hoy dice que reemplazar «es una operación distinta, todavía
no implementada» —`reemplazar_composicion` existe desde P1.2— y añade uno que explique la guarda
de RF‑33, remitiendo a `docs/ERS.md` (UC‑10) y al spec §3.3.

- [ ] **Step 4: Quita el valor por defecto silencioso del mapeo**

En `core/catalog/mapeo.py`, `a_modelo_rendimiento_estimado` pierde el `= ""`:

```python
def a_modelo_rendimiento_estimado(
    composicion: ComposicionAPU, partida: models.Partida, fecha: date, condiciones: str
) -> models.Rendimiento:
```

y el párrafo del docstring que empieza «`condiciones` es opcional aquí porque…» se sustituye por
uno que diga que los dos caminos —`cargar_composicion` y `reemplazar_composicion`— la exigen, y
que la función no tiene valor por defecto justamente para que ningún llamador nuevo pueda omitirla
(spec §3.3).

- [ ] **Step 5: Actualiza los cinco llamadores**

`scripts/seed.py`: pasa las condiciones en la llamada y **borra** el bloque que las asignaba
después (el `select` del `Rendimiento` y el comentario de tres líneas):

```python
    for apu in linea_base.APUS_LINEA_BASE:
        catalogo.cargar_composicion(
            apu,
            lista,
            Dominio.CIVIL,
            linea_base.FECHA_LINEA_BASE,
            CONDICIONES_LINEA_BASE[apu.codigo_partida],
        )
```

Si `select` o `models` quedan sin uso en el archivo, quita el import (ruff `F401` lo marcaría).

`scripts/seed_industrial.py`, `scripts/seed_sistemas.py` y `scripts/seed_telecom.py`: hoy no
declaran condiciones en ninguna parte y dejan `condiciones=''` en la base. Cada uno declara una
constante de módulo junto a sus otras constantes de referencia, con el texto que corresponde a su
procedencia, y la pasa como quinto argumento. Usa exactamente estos textos:

- `seed_industrial.py`: `CONDICIONES_RENDIMIENTO = "rendimiento estimado del caso didactico MNT-001; no proviene de una ejecucion medida"`
- `seed_sistemas.py`: `CONDICIONES_RENDIMIENTO = "rendimiento estimado del caso didactico SIS-001; no proviene de una ejecucion medida"`
- `seed_telecom.py`: `CONDICIONES_RENDIMIENTO = "rendimiento estimado del ejercicio academico ARENAZA; no proviene de una ejecucion medida"`

`scripts/medir_rnf03.py`: es una medición de rendimiento del sistema con datos sintéticos; declara
`CONDICIONES_SINTETICAS = "carga sintetica de la medicion RNF-03; no es un rendimiento de obra"` y
pásala.

Estos textos son deliberados: dicen que el rendimiento **no** viene de una ejecución medida, que es
justo lo que RF‑33 quiere que nadie pueda confundir. No los cambies por un texto más corto.

`tests/integration/test_persistencia.py:251`
(`test_cargar_composicion_dos_veces_lanza_valueerror`) y la llamada que la Tarea 1 dejó en
`test_la_modalidad_a_destajo_sobrevive_el_viaje_por_el_catalogo` necesitan el quinto argumento.
Para la primera usa `"reintento de carga"`; para la segunda,
`"composicion de prueba con jornal y destajo"`.

- [ ] **Step 6: Corre las pruebas, los sembradores y la meta**

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/meta_prototipo.py --hasta P1
```

Después comprueba que los cuatro sembradores siguen corriendo de verdad, cada uno contra una base
temporal propia y **nunca** contra `data/apu.db`. La ruta temporal se calcula con la biblioteca
estándar, que funciona igual en Windows y en Linux:

```bash
TMP=$(uv run python -c "import tempfile;print(tempfile.gettempdir())")
uv run python scripts/seed.py --db "$TMP/p2-civil.db"
uv run python scripts/seed_industrial.py --db "$TMP/p2-industrial.db"
uv run python scripts/seed_sistemas.py --db "$TMP/p2-sistemas.db"
uv run python scripts/seed_telecom.py --db "$TMP/p2-telecom.db"
```

Si alguno de los tres últimos no acepta `--db`, corre `uv run python scripts/<nombre>.py --help`,
usa la bandera que sí tenga y dilo en el informe. Si ninguno la tiene, **no** lo ejecutes contra la
base de trabajo: dilo en el informe como limitación de la comprobación. Reporta las órdenes exactas
que corriste y su salida.

- [ ] **Step 7: Commit**

```bash
git add core/catalog/repositorio.py core/catalog/mapeo.py scripts tests/integration/test_persistencia.py
git commit -m "fix(catalog): rf-33 tambien al crear una partida nueva"
```

---

## Task 3: El spec y la ERS nombran los dos caminos y los dos archivos

**Files:**
- Modify: `docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md` (tabla de §4,
  líneas 179‑192; párrafo de §3.3, líneas 114‑116)
- Modify: `docs/ERS.md` (el enunciado de RF‑33)

**Interfaces:**
- Consumes: lo que las Tareas 1 y 2 dejaron en el código. Esta tarea va **después** de las dos: la
  documentación describe lo que existe, no lo que se planea.
- Produces: nada que otra tarea consuma.

**Qué está mal hoy.** La tabla de §4 del spec lista los archivos que el prototipo toca y omite
`core/models/entidades.py` y `core/catalog/mapeo.py`. Las dos deudas de este plan viven justo ahí,
y la revisión final del ramal anterior lo anotó como hallazgo. Una tabla de arquitectura que no
nombra los archivos donde el diseño falló es una tabla que induce el siguiente error.

- [ ] **Step 1: Añade las dos filas a la tabla de §4 del spec**

En orden, después de la fila de `core/catalog/repositorio.py`:

```markdown
| `core/models/entidades.py` | La línea persistida gana `modalidad` (anulable, como `depreciacion`) |
| `core/catalog/mapeo.py` | La modalidad en la ida y la vuelta; `condiciones` sin valor por defecto |
```

y en la fila de `core/catalog/repositorio.py`, junto a `reemplazar_composicion()`, agrega
`; cargar_composicion() exige las condiciones`.

- [ ] **Step 2: Cierra el párrafo de §3.3 con los dos caminos**

Al párrafo del **requisito funcional nuevo** (líneas 114‑116) añádele una frase: los dos caminos
que persisten una composición —`cargar_composicion`, que crea la partida (UC‑10), y
`reemplazar_composicion`, que corrige la existente (UC‑11)— exigen las condiciones y lanzan
`ValueError` si vienen vacías; ningún ayudante del mapeo las suple con un valor por defecto.

- [ ] **Step 3: Alinea RF‑33 en la ERS**

Busca RF‑33 en `docs/ERS.md` (`grep -n "RF‑33\|RF-33" docs/ERS.md`; el documento usa el guion
tipográfico U+2011 en algunos sitios, así que busca los dos). Si su enunciado menciona solo la
edición, amplíalo a los dos caminos con el mismo vocabulario de UC‑10 y UC‑11 que ya usa el
documento. Si ya cubre los dos, **no lo toques** y dilo en el informe: no hay que inventar un
cambio para justificar el paso.

- [ ] **Step 4: Verifica que no rompiste ninguna meta documental**

```bash
uv run python scripts/meta_prototipo.py --hasta P1
uv run python scripts/meta_datos.py
uv run pytest tests/unit/test_meta_prototipo.py -q
```

Esperado: 6/6 en la meta del prototipo, la meta de datos sin hallazgos y la prueba de la meta en
verde.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md docs/ERS.md
git commit -m "docs(spec): el catalogo y sus dos caminos en la tabla de arquitectura"
```

---

## Task 4: Sesión P2.1 — funciones puras de composición

**Files:**
- Create: `ui/composicion.py`
- Create: `tests/unit/test_composicion.py`
- Modify: `ui/paginas/escenarios.py:191-199` (se va el `_decimal` local) y sus tres usos
  (`:134`, `:137`)

**Interfaces:**
- Consumes: `core.contracts.apu.ComposicionAPU`, `LineaMaterial`, `LineaEquipo`, `LineaManoObra`,
  `ModalidadManoObra`; `core.contracts.item_computo.ItemComputo`, `OrigenTipo`;
  `core.contracts.dominio.Dominio`.
- Produces, para las sesiones P2.2 y P2.3:
  - `ComposicionInvalida(ValueError)`
  - `decimal_desde_texto(texto: str, campo: str) -> Decimal`
  - `composicion_desde_tablas(codigo: str, descripcion: str, unidad: str, rendimiento: str,
    filas_materiales: Sequence[Mapping[str, str]], filas_equipos: Sequence[Mapping[str, str]],
    filas_mano_obra: Sequence[Mapping[str, str]]) -> ComposicionAPU`
  - `item_desde_cantidad(codigo: str, descripcion: str, unidad: str, cantidad: str,
    origen_id: str, dominio: Dominio) -> ItemComputo`

**Tres decisiones ya tomadas, no las revisites.**

1. **Las filas son diccionarios de texto, no DataFrames.** `st.data_editor` devuelve un DataFrame,
   pero convertirlo es trabajo de la página (P2.2), no de este módulo: `ui/composicion.py` no
   importa ni `streamlit` ni `pandas`. Las claves son, exactamente:
   - materiales: `descripcion`, `unidad`, `cantidad`, `precio`
   - equipos: `descripcion`, `cantidad`, `precio`, `depreciacion`
   - mano de obra: `descripcion`, `cantidad`, `sueldo`, `modalidad`
   Una clave ausente se trata como cadena vacía.
2. **El helper se llama `decimal_desde_texto` y es público.** Hoy es `_decimal` dentro de
   `escenarios.py`; un nombre privado importado desde otro módulo es una contradicción. Se mueve
   aquí con ese nombre y `escenarios.py` lo importa. Como `ComposicionInvalida` hereda de
   `ValueError`, el `except (LookupError, ValueError, ArithmeticError, SQLAlchemyError)` de
   `escenarios.py:62` lo sigue atrapando: el comportamiento de esa página no cambia.
3. **`item_desde_cantidad` recibe `dominio`.** El texto de la sesión P2.1 en `PLAN_PROTOTIPO.md`
   lista cinco parámetros, pero `ItemComputo` exige `dominio` y no tiene valor por defecto
   (`core/contracts/item_computo.py:41`): sin él la función no construye nada. Se añade como sexto
   parámetro.

**Sobre `tests/unit/test_arquitectura.py`:** el texto de la sesión dice «agrega "ui" a los paquetes
que vigila, si no está». **Ya está**, en `PAQUETES_FUERA_DEL_NUCLEO` (línea 17), que es lo que usa
`test_el_nucleo_no_conoce_a_los_demas_paquetes`. **No** añadas `ui` al parámetro de
`test_fuera_del_nucleo_solo_se_importa_core_contracts`: ese test exige importar solo
`core.contracts`, y la interfaz usa `core.catalog`, `core.budget` y `core.verification` por diseño
—CLAUDE.md §2 restringe a `core.contracts` a los **adaptadores**, no a `ui/`—. Añadirlo rompería
nueve archivos de golpe. No toques ese archivo en esta tarea.

- [ ] **Step 1: Escribe las pruebas que fallan**

Crea `tests/unit/test_composicion.py`:

```python
"""Funciones puras de composición (Sesión P2.1).

Lo único verificable antes de que existan pruebas de interfaz es lo que se puede llamar sin
Streamlit (spec §4). Estas pruebas fijan ese contorno.
"""

from decimal import Decimal

import pytest

from core.contracts import Dominio, ModalidadManoObra, OrigenTipo
from ui.composicion import (
    ComposicionInvalida,
    composicion_desde_tablas,
    decimal_desde_texto,
    item_desde_cantidad,
)

MATERIALES = [{"descripcion": "Cemento", "unidad": "saco", "cantidad": "7.5", "precio": "8.00"}]
EQUIPOS = [{"descripcion": "Vibrador", "cantidad": "1", "precio": "300.00", "depreciacion": "0.03"}]
MANO_OBRA = [
    {"descripcion": "Obrero de primera", "cantidad": "2", "sueldo": "12.50", "modalidad": "jornal"},
    {"descripcion": "Friso", "cantidad": "1", "sueldo": "6.00", "modalidad": "destajo"},
]


def test_una_tabla_valida_produce_la_composicion_esperada():
    composicion = composicion_desde_tablas(
        "LB-04-VAC", "Vaciado de concreto", "m3", "8", MATERIALES, EQUIPOS, MANO_OBRA
    )

    assert composicion.codigo_partida == "LB-04-VAC"
    assert composicion.rendimiento == Decimal("8")
    assert composicion.materiales[0].cantidad == Decimal("7.5")
    assert composicion.equipos[0].depreciacion == Decimal("0.03")
    assert composicion.mano_obra[1].modalidad is ModalidadManoObra.DESTAJO
    assert composicion.total_obreros == Decimal("2"), "el destajista no cuenta para el bono"


def test_una_cantidad_no_numerica_nombra_el_campo_culpable():
    filas = [{"descripcion": "Cemento", "unidad": "saco", "cantidad": "siete", "precio": "8.00"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert "cantidad" in str(error.value)
    assert "Cemento" in str(error.value)


def test_las_filas_vacias_se_descartan():
    filas = MATERIALES + [{"descripcion": "  ", "unidad": "", "cantidad": "", "precio": ""}]

    composicion = composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert len(composicion.materiales) == 1


def test_un_rendimiento_cero_o_negativo_se_rechaza():
    for valor in ("0", "-3"):
        with pytest.raises(ComposicionInvalida, match="rendimiento"):
            composicion_desde_tablas("P-01", "Prueba", "m3", valor, MATERIALES, [], MANO_OBRA)


def test_la_unidad_con_alias_se_normaliza():
    composicion = composicion_desde_tablas(
        "P-01", "Prueba", "m³", "8", MATERIALES, [], MANO_OBRA
    )

    assert composicion.unidad == "m3"


def test_una_modalidad_desconocida_se_rechaza_nombrando_la_fila():
    filas = [{"descripcion": "Friso", "cantidad": "1", "sueldo": "6.00", "modalidad": "por pieza"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", MATERIALES, [], filas)

    assert "Friso" in str(error.value)
    assert "modalidad" in str(error.value)


def test_una_fila_de_mano_de_obra_sin_modalidad_es_jornal():
    filas = [{"descripcion": "Obrero", "cantidad": "1", "sueldo": "12.50"}]

    composicion = composicion_desde_tablas("P-01", "Prueba", "m3", "8", MATERIALES, [], filas)

    assert composicion.mano_obra[0].modalidad is ModalidadManoObra.JORNAL


def test_item_desde_cantidad_es_trazable_y_manual():
    item = item_desde_cantidad(
        "LB-04-VAC", "Vaciado de concreto", "m3", "1.66", "memoria de calculo 2026-09", Dominio.CIVIL
    )

    assert item.origen_tipo is OrigenTipo.MANUAL
    assert item.cantidad == Decimal("1.66")
    assert item.origen_id == "memoria de calculo 2026-09"


def test_item_desde_cantidad_exige_origen():
    with pytest.raises(ComposicionInvalida, match="origen"):
        item_desde_cantidad("LB-04-VAC", "Vaciado", "m3", "1.66", "   ", Dominio.CIVIL)


def test_decimal_desde_texto_rechaza_lo_que_no_es_finito():
    assert decimal_desde_texto(" 7.5 ", "cantidad") == Decimal("7.5")
    with pytest.raises(ComposicionInvalida, match="cantidad"):
        decimal_desde_texto("Infinity", "cantidad")
```

Comprueba que `Dominio`, `ModalidadManoObra` y `OrigenTipo` se exporten desde `core.contracts`; si
alguno no está, impórtalo de su módulo (`core.contracts.dominio`, `core.contracts.apu`,
`core.contracts.item_computo`) y **no** modifiques `core/contracts/__init__.py`.

- [ ] **Step 2: Corre las pruebas y verifica que fallan**

```bash
uv run pytest tests/unit/test_composicion.py -v
```

Esperado: `ModuleNotFoundError: No module named 'ui.composicion'`.

- [ ] **Step 3: Escribe `ui/composicion.py`**

El módulo, con docstring que explique por qué existe (la lógica vive fuera de `render()` porque es
lo único verificable sin Streamlit, spec §4) y por qué recibe diccionarios de texto y no
DataFrames. Estructura mínima:

```python
class ComposicionInvalida(ValueError):
    """Una tabla de la pantalla no se puede convertir en un APU del contrato."""


def decimal_desde_texto(texto: str, campo: str) -> Decimal:
    """`Decimal` desde el texto del formulario, con el campo culpable en el mensaje."""
```

`decimal_desde_texto` es el `_decimal` de `escenarios.py:191-199` movido tal cual, con dos
cambios: el nombre y `ComposicionInvalida` en lugar de `ValueError`.

Las tres tablas se convierten con un ayudante privado por tipo de línea. Reglas que las pruebas
fijan:

- Una fila cuyos valores sean todos vacíos o espacios se descarta **antes** de convertir nada.
- El mensaje de error lleva el nombre del campo y la descripción de la fila culpable: con tres
  tablas y filas dinámicas, «no es un número decimal válido» a secas no dice dónde mirar.
- `modalidad` vacía o ausente es `JORNAL`. Una modalidad que no esté en `ModalidadManoObra` es
  `ComposicionInvalida`, no un `ValueError` del `StrEnum` escapando sin contexto.
- `rendimiento` se convierte con `decimal_desde_texto(rendimiento, "rendimiento")`. Que sea mayor
  que cero ya lo valida `ComposicionAPU.__post_init__`; envuelve la construcción del contrato en
  `try/except ValueError` y relanza `ComposicionInvalida` **conservando el mensaje original** (con
  `raise ComposicionInvalida(str(error)) from error`), para que la prueba del rendimiento cero
  encuentre la palabra «rendimiento» sin que este módulo duplique la invariante del contrato.
- `item_desde_cantidad` construye con `origen_tipo=OrigenTipo.MANUAL` y envuelve igual: el
  `origen_id` vacío lo rechaza el contrato y aquí solo se traduce la excepción.

No agregues nada que ninguna prueba pida: ni búsqueda MaPreX (es P2.3), ni lectura de CSV, ni
caché.

- [ ] **Step 4: Corre las pruebas hasta el verde**

```bash
uv run pytest tests/unit/test_composicion.py -v
```

- [ ] **Step 5: `escenarios.py` usa el conversor compartido**

Borra `_decimal` de `ui/paginas/escenarios.py` (líneas 191‑199), importa
`from ui.composicion import decimal_desde_texto` y cambia los dos usos (`:134` y `:137`). Si
`InvalidOperation` queda sin uso en el archivo, quita el import.

- [ ] **Step 6: Suite completa, ruff, arquitectura y la meta P7**

```bash
uv run pytest -q
uv run ruff check .
uv run pytest tests/unit/test_arquitectura.py tests/unit/test_ui_importable.py -q
uv run python scripts/meta_prototipo.py --hasta P2
```

Esperado: todo verde; la meta P7 («ui/composicion.py existe y no importa streamlit») en **OK** y la
P8 todavía en PENDIENTE —la página `componer.py` es la sesión P2.2, no esta—. Reporta la tabla de
la meta tal cual en tu informe.

- [ ] **Step 7: Commit**

```bash
git add ui/composicion.py ui/paginas/escenarios.py tests/unit/test_composicion.py
git commit -m "feat(ui): funciones puras de composicion de apu"
```

---

## Cierre de la sesión

Al terminar las cuatro tareas:

- `uv run pytest -q` y `uv run ruff check .` en verde.
- `uv run python scripts/meta_prototipo.py --hasta P2` con P1–P7 en OK y P8 en PENDIENTE (7 de 8).
- `git diff p-base --stat -- core/` muestra **solo** lo de P1.1/P1.2 más las dos deudas saldadas:
  `contracts/apu.py`, `costing/motor.py`, `catalog/repositorio.py`, `catalog/mapeo.py` y
  `models/entidades.py`. Ninguna tarea de este plan toca `core/verification/` ni `core/budget/`.
- Las sesiones P2.2, P2.3 y P2.4 reciben su propio plan ejecutable.
