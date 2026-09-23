# AREN.IA — fases P0 y P1: plan de implementación

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Dejar documentado el expediente de la decisión D9 y llevar al núcleo la modalidad de mano
de obra por línea (jornal o destajo), sin mover ni un céntimo de la línea base.

**Architecture:** El cambio al núcleo es aditivo y retrocompatible: un campo con valor por defecto en
`LineaManoObra` y una rama en `calcular_apu` que separa la mano de obra en dos sumandos. El catálogo
gana el reemplazo de composiciones que hoy no existe, y una lista de precios en USD derivada de la
referencia MaPreX. Ningún commit de esta fase toca `adapters/` ni `ml/`, para que la guardia del
núcleo pase.

**Tech Stack:** Python 3.12 · `Decimal` · SQLAlchemy 2 · pytest · ruff · uv

**Spec:**
[docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md](../specs/2026-09-16-prototipo-composicion-apu-design.md)

**Plan de sesiones:** [PLAN_PROTOTIPO.md](../../../PLAN_PROTOTIPO.md) — este documento desarrolla
las sesiones P0.1 a P1.2. Las fases P2 a P5 reciben su propio plan ejecutable al abrirse, porque sus
tareas dependen de decisiones que se toman al cerrar GP0 y GP1.

## Global Constraints

- **`Decimal` en todo lo monetario y dimensional.** Nunca `float` en cantidades, precios, factores ni
  rendimientos. Se construye siempre desde texto: `Decimal("6")`, nunca `Decimal(6.0)`.
- **Se redondea solo al presentar**, a dos decimales con `ROUND_HALF_UP`. El único sitio del núcleo
  que redondea es `core/budget/excel.py`.
- **`tests/unit/test_costing.py` y `tests/fixtures/apu_linea_base.py` NO se modifican.** Si una tarea
  parece exigirlo, la tarea está mal: detente y reporta.
- **Ningún commit que toque `core/` puede tocar `adapters/` ni `ml/`** en el mismo commit
  (`scripts/guardia_nucleo.py`).
- **ruff:** `line-length = 100`, `target-version = "py312"`, reglas `E, F, W, I, B, UP, N`.
- **Idioma:** código, docstrings y documentación en español; **identificadores sin tildes**.
- **Commits:** Conventional Commits en español, **asunto sin tildes**.
- **Pruebas:** `uv run pytest` corre con `-q --strict-markers`; la CI añade `-W error`. Un aviso es
  un fallo.
- **Entorno:** `uv sync` para el grupo dev. Los extras (`ml`, `ui`, `api`, `civil`) no hacen falta en
  estas dos fases.

---

## Estructura de archivos

| Archivo | Responsabilidad | Tarea |
|---|---|---|
| `docs/ERS.md` | Requisitos: UC‑10, UC‑11 y los RF nuevos | 1 |
| `docs/fuentes/README.md` | Ficha de procedencia de cada documento archivado | 1 |
| `docs/fuentes/2026-09-16-nota-practica-apu.md` | La comunicación personal, transcrita y encuadrada | 1 |
| `scripts/meta_prototipo.py` | Auditoría del avance del sprint por fases | 2 |
| `tests/unit/test_meta_prototipo.py` | Prueba de la meta | 2 |
| `docs/bitacora/2026-09-16-P0-hallazgo-destajo.md` | El hallazgo: el contrato no expresa el artículo 114 | 3 |
| `docs/dossier_g0.md` | D9 nueva; D4 actualizada | 3 |
| `docs/arquitectura.md` | Vista de la página de composición | 3 |
| `core/contracts/apu.py` | `ModalidadManoObra` y el campo en `LineaManoObra` | 4 |
| `core/costing/motor.py` | La mano de obra en dos sumandos | 4 |
| `tests/unit/test_costing_destajo.py` | Las cinco pruebas de la modalidad | 4 |
| `core/catalog/repositorio.py` | `reemplazar_composicion` | 5 |
| `tests/integration/test_persistencia.py` | Las tres pruebas del reemplazo | 5 |
| `scripts/lista_maprex_usd.py` | Deriva la lista canónica en USD | 6 |
| `tests/unit/test_lista_maprex_usd.py` | Prueba de la derivación | 6 |
| `scripts/seed.py` | Siembra los cinco rendimientos de la línea base | 7 |

---

## Task 1: ERS, fuentes y la nota de campo

**Files:**
- Modify: `docs/ERS.md`
- Create: `docs/fuentes/README.md`
- Create: `docs/fuentes/2026-09-16-nota-practica-apu.md`

**Interfaces:**
- Consumes: nada.
- Produces: los identificadores **UC‑10**, **UC‑11** y los RF nuevos, que las tareas 3 y 4 citan en
  la bitácora y en los docstrings.

- [ ] **Step 1: Leer cómo están numerados los casos de uso y requisitos**

Run: `grep -n -E "^#+ *(UC-[0-9]+|RF-[0-9]+)" docs/ERS.md | tail -20`
Expected: la lista de UC y RF existentes; anota el último número de cada serie para continuarla.

- [ ] **Step 2: Añadir UC-10 y UC-11 a la ERS**

Sigue exactamente el formato de los casos de uso que ya están en el archivo (actor, precondición,
flujo principal numerado, flujos alternativos, postcondición). Contenido:

- **UC‑10 Componer una partida.** El proyectista declara código, descripción y unidad; arma las tres
  tablas de insumos; declara el rendimiento con sus condiciones; ve el precio unitario; guarda.
  Flujo alternativo: la partida ya existe con composición → se ofrece editarla (UC‑11).
- **UC‑11 Editar una partida compuesta.** Precondición: la partida existe y tiene composición. El
  reemplazo registra un rendimiento nuevo y conserva el anterior en el histórico.

Requisitos funcionales nuevos, con el número que siga al último de la ERS:

- «El sistema no persiste una composición cuyo rendimiento no haya sido declarado explícitamente
  junto con sus condiciones.»
- «La modalidad de la mano de obra se declara por línea: jornal o destajo.»
- «El precio sugerido desde la referencia de mercado es editable por quien presupuesta.»

Marca **RF‑16** como satisfecho por UC‑10 (hoy dice que espera un flujo de creación de partidas).

- [ ] **Step 3: Escribir la ficha de procedencia de las fuentes**

Crea `docs/fuentes/README.md` con una tabla: archivo · qué es · Gaceta y fecha · de dónde se
descargó · qué sección del spec lo cita. Documentos a fichar:

`LOTTT_GO_6076_Ext_2012-05-07.pdf` · `CCT_Construccion_GO_6752_Ext_2023-07-06.pdf` ·
`Ley_Seguro_Social_GO_4322_Ext_1991_CEPAL.pdf` y `_Justia.pdf` · `Chacin_2008_FCAS_URU.pdf` ·
`Dodi_Salas_2019_FCAS_UJAP.pdf` · `Bases_Anteproyecto_BIM5D_APU.docx` ·
`Estado_del_Arte_BIM5D_ML_APU.pdf`.

Cierra con dos salvedades, textuales:

> El PDF de la convención colectiva proviene de un host comercial privado, no de un portal oficial
> de Gaceta. El texto es primario, pero antes de citarlo en la defensa debe cotejarse contra una
> copia oficial.

> El dominio `leyes.io`, primer resultado de buscador para el artículo 114 de la LOTTT, redirige
> desde 2026 a un dominio de spam. No se cita.

- [ ] **Step 4: Transcribir la nota de campo**

Crea `docs/fuentes/2026-09-16-nota-practica-apu.md`. Encabézalo con este bloque, y debajo el texto
literal de la nota:

```markdown
**Naturaleza.** Comunicación personal con un profesional de presupuestos de obra, recibida como
mensajes de voz el 2026-09-16. El informante conserva su anonimato por decisión del autor.

**Cómo se cita.** En APA 7 una comunicación personal se cita en el texto y no entra en la lista de
referencias: `(comunicación personal, 16 de septiembre de 2026)`. Esta transcripción existe como
anexo consultable, no como referencia bibliográfica.

**Qué papel cumple.** No prueba la existencia del salario por unidad de obra: eso lo establece el
artículo 114 de la LOTTT. Esta nota testimonia que esa modalidad se usa en obra y cómo se refleja
en el análisis de precios unitarios.
```

- [ ] **Step 5: Verificar que la meta de datos sigue verde**

Run: `uv run python scripts/meta_datos.py`
Expected: `RESULTADO: 3/3 metas OK`. Si D1 falla, una oración nueva presenta los datos del
repositorio como reales: reescríbela.

- [ ] **Step 6: Commit**

```bash
git add docs/ERS.md docs/fuentes/
git commit -m "docs(ers): casos de uso de composicion y edicion de partidas"
```

---

## Task 2: La meta del sprint

**Files:**
- Create: `scripts/meta_prototipo.py`
- Create: `tests/unit/test_meta_prototipo.py`
- Read for pattern: `scripts/meta_asistente.py`, `scripts/meta_datos.py`

**Interfaces:**
- Consumes: `scripts.meta_alpha.Estado`, `Fila`, `_filas_a_json`, `render_tabla` (los importan las
  otras metas del repositorio).
- Produces: `uv run python scripts/meta_prototipo.py [--hasta P0|P1|P2|P3|P4|P5] [--json]`, que las
  tareas 3 a 7 usan como criterio de cierre.

- [ ] **Step 1: Leer el patrón exacto**

Run: `sed -n '1,80p' scripts/meta_asistente.py`
Expected: el encabezado, el diccionario de títulos, cómo se declara `--hasta` y cómo se evalúa cada
meta. **Copia esa estructura**; no inventes una nueva.

- [ ] **Step 2: Escribir la prueba primero**

```python
"""La meta del sprint del prototipo: que audite fases y no se salte ninguna."""

from __future__ import annotations

import pytest

from scripts.meta_prototipo import FASES, TITULOS, main


def test_toda_meta_declarada_tiene_titulo():
    for codigo in (codigo for metas in FASES.values() for codigo in metas):
        assert codigo in TITULOS, f"la meta {codigo} no tiene titulo"


def test_las_fases_van_de_p0_a_p5():
    assert list(FASES) == ["P0", "P1", "P2", "P3", "P4", "P5"]


def test_hasta_una_fase_inexistente_se_rechaza():
    with pytest.raises(SystemExit):
        main(["--hasta", "P9"])
```

- [ ] **Step 3: Ejecutar la prueba y verificar que falla**

Run: `uv run pytest tests/unit/test_meta_prototipo.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.meta_prototipo'`.

- [ ] **Step 4: Escribir la meta**

Crea `scripts/meta_prototipo.py` siguiendo el patrón de `meta_asistente.py`. Las metas, agrupadas
por fase:

| Fase | Metas |
|---|---|
| P0 | **P1** UC‑10 y UC‑11 en la ERS · **P2** `docs/fuentes/README.md` ficha cada archivo de `docs/fuentes/` · **P3** D9 en el dossier |
| P1 | **P4** `ModalidadManoObra` existe en `core.contracts.apu` · **P5** la línea base reproduce su precio unitario · **P6** `reemplazar_composicion` existe en `Catalogo` |
| P2 | **P7** `ui/composicion.py` no importa streamlit · **P8** `ui.paginas.componer` está en `test_ui_importable.py` |
| P3 | **P9** la prueba de extremo a extremo existe y pasa |
| P4 | **P10** hay al menos una prueba que usa `AppTest` · **P11** ningún módulo de `ml/` referencia el corpus simulado |
| P5 | **P12** la bitácora del sprint existe |

`--hasta <fase>` evalúa solo las metas de esa fase y las anteriores, y sale con código 1 si alguna
no está en OK. `--hasta` con una fase que no esté en `FASES` termina con `SystemExit`.

- [ ] **Step 5: Ejecutar la prueba y verificar que pasa**

Run: `uv run pytest tests/unit/test_meta_prototipo.py -v`
Expected: 3 passed.

- [ ] **Step 6: Ver el tablero**

Run: `uv run python scripts/meta_prototipo.py --hasta P0`
Expected: tabla con P1, P2 y P3; P1 y P2 en OK tras la tarea 1, P3 en PENDIENTE hasta la tarea 3.

- [ ] **Step 7: Commit**

```bash
git add scripts/meta_prototipo.py tests/unit/test_meta_prototipo.py
git commit -m "feat(scripts): meta del sprint del prototipo auditada por fases"
```

---

## Task 3: El hallazgo, D9 y la arquitectura — compuerta GP0

**Files:**
- Create: `docs/bitacora/2026-09-16-P0-hallazgo-destajo.md`
- Modify: `docs/dossier_g0.md`
- Modify: `docs/arquitectura.md`

**Interfaces:**
- Consumes: los identificadores UC‑10 y UC‑11 de la tarea 1; las fuentes de `docs/fuentes/`.
- Produces: la decisión **D9**, que la tarea 4 cita en su commit y en el docstring del contrato.

- [ ] **Step 1: Confirmar el texto del artículo 114 en el archivo local**

Run: `grep -n -A4 "unidad de obra, por pieza o a destajo" docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt | head -30`
Expected: el encabezado marginal y el texto del artículo 114. **Cita desde aquí**, no de memoria.

- [ ] **Step 2: Confirmar la cláusula 1 de la convención colectiva**

Run: `grep -n -B2 -A6 "POR UNIDAD DE OBRA, POR PIEZA O A DESTAJO" docs/fuentes/CCT_Construccion_GO_6752_Ext_2023-07-06.txt | head -30`
Expected: la definición del trabajador a destajo y la frase sobre el Tabulador de Oficios y Salarios.

- [ ] **Step 3: Escribir la bitácora del hallazgo**

`docs/bitacora/2026-09-16-P0-hallazgo-destajo.md` debe decir, en este orden:

1. **Qué se intentó.** Expresar en `ComposicionAPU` una mano de obra que cobra por unidad instalada.
2. **Por qué no se puede.** `calcular_apu` aplica `(1 + fcas)` a toda línea de mano de obra
   (`core/costing/motor.py`), suma `bono × total_obreros` y divide el bloque entre el rendimiento.
   No hay bandera por línea y `ParametrosCosto` se congela por presupuesto, no por partida.
3. **Por qué es un hallazgo y no un capricho.** Las dos citas de los pasos 1 y 2.
4. **Por qué la hipótesis central no se ve afectada.** Dice que `core/` no cambia **al agregar un
   dominio**; una modalidad salarial no es un dominio. `scripts/guardia_nucleo.py` solo falla si un
   commit toca `core/` junto a `adapters/` o `ml/`.
5. **Las cuatro opciones evaluadas** y por qué se elige la modalidad por línea: modalidad por línea ·
   sueldo sintético fuera del núcleo (precedente en `scripts/seed_telecom.py`) · no implementarlo ·
   cuarta categoría de subcontratos.

- [ ] **Step 4: Añadir D9 y actualizar D4 en el dossier**

Sigue el formato exacto de D1–D8 (párrafo, **Opciones:**, **Recomendación:**).

**D9. Modalidad de mano de obra por línea (cambio a un contrato declarado estable).** Con el
fundamento de la bitácora. Recomendación: implementarla, por ser aditiva y retrocompatible.

**D4** (ya existe): añade que el FCAS del 600 % **no tiene fuente normativa publicada**. No lo
publican el CIV, la Cámara Venezolana de la Construcción, COVENIN ni MaPreX. Valores publicados:
198 %–293 % (Chacín, 2008, `docs/fuentes/Chacin_2008_FCAS_URU.pdf`) y 78 %–2 386 % según qué
cláusulas se incluyan (Dodi y Salas, 2019, `docs/fuentes/Dodi_Salas_2019_FCAS_UJAP.pdf`, cálculo
dominado por la hiperinflación de 2018). Recomendación: declararlo parámetro configurable de la
línea base del caso de estudio.

Añade también el hallazgo que **respalda** la fórmula vigente: la cláusula 20 de la convención dice
que el bono de alimentación *«no tiene carácter salarial, a ningún efecto legal o contractual»*, y
el motor ya lo suma aparte sin multiplicarlo por el FCAS.

- [ ] **Step 5: Añadir la vista de arquitectura**

En `docs/arquitectura.md`, sección de la vista lógica: `ui/composicion.py` es lógica pura probada sin
Streamlit; `ui/paginas/componer.py` solo pinta; las ayudas de aprendizaje automático se invocan desde
`ui/` con importación perezosa, nunca desde `core/`.

- [ ] **Step 6: Verificar la compuerta**

Run: `uv run python scripts/meta_prototipo.py --hasta P0 && uv run python scripts/meta_datos.py`
Expected: las tres metas de P0 en OK y `3/3 metas OK`.

- [ ] **Step 7: Commit**

```bash
git add docs/bitacora/2026-09-16-P0-hallazgo-destajo.md docs/dossier_g0.md docs/arquitectura.md
git commit -m "docs(g0): decision d9 sobre la modalidad de mano de obra"
```

> **GP0 queda cruzada aquí.** No avances a la tarea 4 sin que las metas de P0 estén en OK.

---

## Task 4: La modalidad en el núcleo

**Files:**
- Create: `tests/unit/test_costing_destajo.py`
- Modify: `core/contracts/apu.py`
- Modify: `core/costing/motor.py`
- **No tocar:** `tests/unit/test_costing.py`, `tests/fixtures/apu_linea_base.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `core.contracts.apu.ModalidadManoObra` con miembros `JORNAL` y `DESTAJO`, y
  `LineaManoObra(descripcion, cantidad, sueldo, modalidad=ModalidadManoObra.JORNAL)`. Las tareas de
  las fases P2 y P3 construyen líneas con esa firma.

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
"""Modalidad de mano de obra por linea: jornal frente a destajo.

El destajo es el salario por unidad de obra del articulo 114 de la LOTTT: entra completo al precio
unitario, sin factor de costos asociados al salario, sin bono de alimentacion y sin dividirse entre
el rendimiento. Ver docs/bitacora/2026-09-16-P0-hallazgo-destajo.md y la decision D9.
"""

from __future__ import annotations

from decimal import Decimal

from core.contracts.apu import (
    ComposicionAPU,
    LineaManoObra,
    ModalidadManoObra,
    ParametrosCosto,
)
from core.costing import calcular_apu
from tests.fixtures import apu_linea_base as lb

TOLERANCIA = Decimal("0.01")


def _mixta() -> ComposicionAPU:
    """Una partida con un ayudante a jornal y un instalador a destajo."""
    return ComposicionAPU(
        codigo_partida="X-01",
        descripcion="Instalacion de piso ceramico",
        unidad="m2",
        rendimiento=Decimal("50"),
        mano_obra=(
            LineaManoObra("Ayudante", Decimal("2"), Decimal("3")),
            LineaManoObra(
                "Instalador a destajo",
                Decimal("1"),
                Decimal("6"),
                ModalidadManoObra.DESTAJO,
            ),
        ),
    )


def test_una_linea_sin_modalidad_es_jornal():
    linea = LineaManoObra("Albanil de 1ra", Decimal("1"), Decimal("5"))

    assert linea.modalidad is ModalidadManoObra.JORNAL


def test_el_destajo_entra_completo():
    """6 USD por m2 instalado son 6 USD en el APU: ni FCAS, ni bono, ni division."""
    composicion = ComposicionAPU(
        codigo_partida="X-02",
        descripcion="Instalacion a destajo",
        unidad="m2",
        rendimiento=Decimal("50"),
        mano_obra=(
            LineaManoObra(
                "Instalador", Decimal("1"), Decimal("6"), ModalidadManoObra.DESTAJO
            ),
        ),
    )

    resultado = calcular_apu(composicion, ParametrosCosto())

    assert resultado.mano_obra == Decimal("6")


def test_total_obreros_excluye_el_destajo():
    """Un subcontratista que cobra por metro no devenga bono de alimentacion."""
    assert _mixta().total_obreros == Decimal("2")


def test_la_composicion_mixta_suma_los_dos_bloques():
    parametros = ParametrosCosto()
    composicion = _mixta()

    resultado = calcular_apu(composicion, parametros)

    jornal = (
        Decimal("2") * Decimal("3") * (1 + parametros.fcas)
        + parametros.bono_alimentacion * Decimal("2")
    ) / Decimal("50")
    assert resultado.mano_obra == jornal + Decimal("6")


def test_la_linea_base_no_se_mueve():
    """Caracterizacion: con todas las lineas en JORNAL, el resultado es el de siempre."""
    for apu in lb.APUS_LINEA_BASE:
        resultado = calcular_apu(apu, lb.PARAMETROS_LINEA_BASE)
        esperado = lb.PRECIO_UNITARIO_ESPERADO[apu.codigo_partida]
        assert abs(resultado.precio_unitario - esperado) <= TOLERANCIA, apu.codigo_partida
```

- [ ] **Step 2: Ejecutar y verificar que fallan por el motivo correcto**

Run: `uv run pytest tests/unit/test_costing_destajo.py -v`
Expected: FAIL con `ImportError: cannot import name 'ModalidadManoObra'`. Si falla por otra razón,
detente: la prueba está mal escrita.

- [ ] **Step 3: Añadir la enumeración y el campo al contrato**

En `core/contracts/apu.py`, junto a `TipoRendimiento` (que ya usa `StrEnum`):

```python
class ModalidadManoObra(StrEnum):
    """Cómo se remunera una línea de mano de obra.

    JORNAL es el salario por unidad de tiempo: recibe el factor de costos asociados al salario y
    el bono de alimentación, y se divide entre el rendimiento.
    DESTAJO es el salario por unidad de obra del artículo 114 de la LOTTT: entra completo al
    precio unitario. Bajo esta modalidad, `sueldo` NO es un sueldo diario sino el precio por
    unidad de partida (decisión D9; ver docs/bitacora/2026-09-16-P0-hallazgo-destajo.md).
    """

    JORNAL = "jornal"
    DESTAJO = "destajo"
```

Y en `LineaManoObra`, el campo al final para no romper ninguna construcción posicional:

```python
    modalidad: ModalidadManoObra = ModalidadManoObra.JORNAL
```

Actualiza el docstring de la clase para nombrar la doble semántica de `sueldo`.

- [ ] **Step 4: Excluir el destajo de `total_obreros`**

En `ComposicionAPU`:

```python
    @property
    def total_obreros(self) -> Decimal:
        """Obreros que devengan bono de alimentación: las líneas a destajo no cuentan."""
        return sum(
            (
                linea.cantidad
                for linea in self.mano_obra
                if linea.modalidad is ModalidadManoObra.JORNAL
            ),
            Decimal(0),
        )
```

- [ ] **Step 5: Partir la mano de obra en dos sumandos**

En `core/costing/motor.py`, reemplaza el bloque de mano de obra por:

```python
    jornal = [
        linea
        for linea in composicion.mano_obra
        if linea.modalidad is ModalidadManoObra.JORNAL
    ]
    sueldos_con_fcas = sum(
        (linea.total * (1 + parametros.fcas) for linea in jornal), Decimal(0)
    )
    bono_total = parametros.bono_alimentacion * composicion.total_obreros
    mano_obra_jornal = (sueldos_con_fcas + bono_total) / composicion.rendimiento

    # El destajo entra completo: es precio por unidad de partida, no sueldo por dia.
    mano_obra_destajo = sum(
        (
            linea.total
            for linea in composicion.mano_obra
            if linea.modalidad is ModalidadManoObra.DESTAJO
        ),
        Decimal(0),
    )
    mano_obra = mano_obra_jornal + mano_obra_destajo
```

Añade `ModalidadManoObra` al import del módulo y actualiza el bloque de fórmulas del docstring.

- [ ] **Step 6: Ejecutar las pruebas nuevas**

Run: `uv run pytest tests/unit/test_costing_destajo.py -v`
Expected: 5 passed.

- [ ] **Step 7: Ejecutar la suite completa y confirmar que la línea base no se movió**

Run: `uv run pytest -q`
Expected: todo verde. **`tests/unit/test_costing.py` debe pasar sin haber sido modificado.**

Run: `git status --short tests/unit/test_costing.py tests/fixtures/apu_linea_base.py`
Expected: salida vacía. Si aparecen modificados, revierte: `git checkout -- <archivo>`.

- [ ] **Step 8: Verificar la guardia del núcleo y el estilo**

Run: `uv run ruff check . && git diff --stat -- adapters/ ml/`
Expected: `All checks passed!` y diff vacío — este commit toca solo `core/` y `tests/`.

- [ ] **Step 9: Commit**

```bash
git add core/contracts/apu.py core/costing/motor.py tests/unit/test_costing_destajo.py
git commit -m "feat(core): modalidad de mano de obra por linea, jornal o destajo"
```

Run: `uv run python scripts/guardia_nucleo.py --base p-base`
Expected: `guardia del nucleo: OK`.

---

## Task 5: Reemplazar la composición de una partida

**Files:**
- Modify: `core/catalog/repositorio.py`
- Modify: `tests/integration/test_persistencia.py`

**Interfaces:**
- Consumes: `ResumenCarga` y `_resolver_insumo`, ya existentes en el módulo.
- Produces: `Catalogo.reemplazar_composicion(composicion, lista, dominio, fecha_rendimiento) -> ResumenCarga`,
  que la página de composición (fase P2) llama cuando la partida ya existe.

- [ ] **Step 1: Leer el método que se va a reflejar**

Run: `grep -n -A45 "def cargar_composicion" core/catalog/repositorio.py`
Expected: la resolución de insumos, el `flush()` y el `ValueError` de la partida ya compuesta.

- [ ] **Step 2: Escribir las pruebas que fallan**

Añade a `tests/integration/test_persistencia.py`, imitando el estilo de las pruebas vecinas:

Añade primero `replace` a los imports del archivo (`from dataclasses import replace`); el resto de
lo que se usa ya está importado allí.

El fixture `sesion` de `tests/integration/conftest.py` **entrega la línea base ya sembrada y
confirmada**, así que estas pruebas no cargan nada: reemplazan sobre una partida que ya existe.

```python
def test_reemplazar_composicion_permite_corregir_una_partida(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    corregido = replace(
        linea_base.APU_RELLENO,
        rendimiento=linea_base.APU_RELLENO.rendimiento + Decimal("1"),
    )

    resumen = catalogo.reemplazar_composicion(
        corregido, lista, contracts.Dominio.CIVIL, linea_base.FECHA_LINEA_BASE
    )

    assert resumen.partida.codigo == "LB-05-REL"
    assert Catalogo(sesion).composicion("LB-05-REL") == corregido


def test_reemplazar_conserva_el_rendimiento_anterior_en_el_historico(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    original = linea_base.APU_RELLENO.rendimiento
    corregido = replace(linea_base.APU_RELLENO, rendimiento=original + Decimal("1"))

    catalogo.reemplazar_composicion(
        corregido, lista, contracts.Dominio.CIVIL, linea_base.FECHA_LINEA_BASE
    )

    valores = [rendimiento.valor for rendimiento in catalogo.rendimientos("LB-05-REL")]
    assert original in valores
    assert corregido.rendimiento in valores


def test_reemplazar_una_partida_inexistente_lanza_lookuperror(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    inventada = replace(linea_base.APU_RELLENO, codigo_partida="LB-99-NADA")

    with pytest.raises(LookupError, match="LB-99-NADA"):
        catalogo.reemplazar_composicion(
            inventada, lista, contracts.Dominio.CIVIL, linea_base.FECHA_LINEA_BASE
        )
```

La primera prueba compara la composición reconstruida con el contrato completo, no solo su
rendimiento: es el mismo criterio que usa `test_sembrar_es_idempotente`, ya en el archivo.

- [ ] **Step 3: Ejecutar y verificar que fallan**

Run: `uv run pytest tests/integration/test_persistencia.py -k reemplazar -v`
Expected: FAIL con `AttributeError: 'Catalogo' object has no attribute 'reemplazar_composicion'`.

- [ ] **Step 4: Implementar el método**

En `core/catalog/repositorio.py`, junto a `cargar_composicion`:

```python
    def reemplazar_composicion(
        self,
        composicion: ComposicionAPU,
        lista: models.ListaPrecios,
        dominio: Dominio,
        fecha_rendimiento: date,
    ) -> ResumenCarga:
        """Sustituye el desglose de una partida existente y registra un rendimiento nuevo.

        El rendimiento anterior NO se pisa: queda en el histórico, porque la serie de
        rendimientos de una partida es evidencia (UC-11). No hace `commit`: eso es de la capa
        que llama, como en `cargar_composicion`.
        """
        partida = self._buscar_partida(composicion.codigo_partida)
        if partida is None:
            raise LookupError(
                f"no se puede reemplazar la composición de {composicion.codigo_partida}: "
                "la partida no existe en el catálogo"
            )
        for linea in list(partida.composicion):
            self._sesion.delete(linea)
        self._sesion.flush()
        return self._cargar_lineas(partida, composicion, lista, dominio, fecha_rendimiento)
```

`_cargar_lineas` **no existe todavía**: hay que extraerlo primero. Son las cinco líneas finales de
`cargar_composicion` (`core/catalog/repositorio.py:166-172`), las que van después de crear o
encontrar la partida. Sácalas a un método privado y haz que `cargar_composicion` lo llame, de modo
que la resolución de insumos viva en un solo sitio:

```python
    def _cargar_lineas(
        self,
        partida: models.Partida,
        composicion: ComposicionAPU,
        lista: models.ListaPrecios,
        fecha_rendimiento: date,
    ) -> ResumenCarga:
        """Persiste líneas, insumos, precios y el rendimiento estimado de una partida ya creada."""
        resumen = ResumenCarga(partida=partida)
        lineas = lineas_de(composicion)
        insumos = [self._resolver_insumo(linea, lista, resumen) for linea in lineas]
        self._sesion.add_all(a_modelo_lineas(lineas, partida, insumos))
        self._sesion.add(a_modelo_rendimiento_estimado(composicion, partida, fecha_rendimiento))
        self._sesion.flush()
        return resumen
```

`cargar_composicion` queda terminando en `return self._cargar_lineas(partida, composicion, lista, fecha_rendimiento)`
y conserva intacto su `ValueError` de partida ya compuesta: sigue sin ser reentrante, y eso es
correcto — reemplazar es la operación distinta que añade esta tarea. El parámetro `dominio` solo lo
usa `a_modelo_partida`, así que no entra en `_cargar_lineas`; en `reemplazar_composicion` se acepta
por simetría de firma con `cargar_composicion` y se ignora, lo cual debe decirlo el docstring.

- [ ] **Step 5: Ejecutar las pruebas**

Run: `uv run pytest tests/integration/test_persistencia.py -k reemplazar -v`
Expected: 3 passed.

- [ ] **Step 6: Confirmar que no se rompió la carga original**

Run: `uv run pytest tests/integration/test_persistencia.py -q`
Expected: todo verde, incluida `test_cargar_composicion_dos_veces_lanza_valueerror`, que sigue
siendo el comportamiento correcto de `cargar_composicion`.

- [ ] **Step 7: Commit**

```bash
git add core/catalog/repositorio.py tests/integration/test_persistencia.py
git commit -m "feat(catalog): reemplazo de la composicion de una partida existente"
```

---

## Task 6: La lista de precios MaPreX en USD

**Files:**
- Create: `scripts/lista_maprex_usd.py`
- Create: `tests/unit/test_lista_maprex_usd.py`
- Output: `data/precios/maprex_2026-07/lista_maprex_usd.csv`

**Interfaces:**
- Consumes: `data/precios/maprex_2026-07/referencia_{civil,telecom,industrial,sistemas}.csv`, con
  columnas `tipo,insumo,unidad,precio_bs,bono_bs,factor_depreciacion,precio_usd,fecha_vigencia,archivo,ref_maprex,notas`.
- Produces: un CSV con las columnas canónicas `tipo,insumo,unidad,precio` que
  `core.catalog.precios.leer_lista_precios` acepta sin cambios.

- [ ] **Step 1: Confirmar las columnas de origen y el formato canónico**

Run: `head -1 data/precios/maprex_2026-07/referencia_civil.csv && grep -n "COLUMNAS_ARCHIVO" core/catalog/precios.py`
Expected: la cabecera de once columnas y `COLUMNAS_ARCHIVO = ("tipo", "insumo", "unidad", "precio")`.

- [ ] **Step 2: Escribir la prueba que falla**

```python
"""La lista canonica en USD derivada de la referencia MaPreX."""

from __future__ import annotations

from decimal import Decimal

from core.catalog.precios import COLUMNAS_ARCHIVO
from scripts.lista_maprex_usd import RUTA_SALIDA, filas_canonicas


def test_las_columnas_son_las_que_espera_el_cargador():
    filas = filas_canonicas()

    assert tuple(filas[0]) == COLUMNAS_ARCHIVO


def test_todo_precio_es_decimal_positivo_leido_desde_texto():
    for fila in filas_canonicas():
        precio = Decimal(fila["precio"])
        assert precio > 0, fila["insumo"]


def test_no_hay_insumos_duplicados_por_tipo_y_descripcion():
    filas = filas_canonicas()
    claves = [(fila["tipo"], fila["insumo"], fila["unidad"]) for fila in filas]

    assert len(claves) == len(set(claves))


def test_la_ruta_de_salida_esta_dentro_de_la_referencia():
    assert RUTA_SALIDA.parent.name == "maprex_2026-07"
```

- [ ] **Step 3: Ejecutar y verificar que falla**

Run: `uv run pytest tests/unit/test_lista_maprex_usd.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.lista_maprex_usd'`.

- [ ] **Step 4: Escribir el script**

`filas_canonicas() -> list[dict[str, str]]` lee los cuatro CSV con `csv.DictReader`, toma
`precio_usd` como `precio`, descarta duplicados por `(tipo, insumo, unidad)` conservando el primero,
y ordena por esa misma clave para que la salida sea determinista. `main()` escribe `RUTA_SALIDA`.
Los precios se copian **como texto**: no pasan por `float` en ningún punto. Declara en el docstring
que la referencia está en USD por conversión con la tasa declarada de 633,3644 Bs/USD al 01/07/2026
y que MaPreX es referencia de mercado, no ronda de cotizaciones vigente.

- [ ] **Step 5: Ejecutar las pruebas y generar la lista**

Run: `uv run pytest tests/unit/test_lista_maprex_usd.py -v && uv run python scripts/lista_maprex_usd.py`
Expected: 4 passed y el CSV escrito. Comprueba el contenido:

Run: `head -3 data/precios/maprex_2026-07/lista_maprex_usd.csv`
Expected: la cabecera `tipo,insumo,unidad,precio` y dos filas con precio decimal con punto.

- [ ] **Step 6: Comprobar que el cargador oficial la acepta**

Run: `uv run python -c "from core.catalog.precios import leer_lista_precios; from pathlib import Path; filas = leer_lista_precios(Path('data/precios/maprex_2026-07/lista_maprex_usd.csv')); print(len(filas), filas[0])"`
Expected: el número de filas y la primera como `PrecioLeido`. Si lanza `ValueError`, el CSV no
cumple el formato canónico.

- [ ] **Step 7: Commit**

```bash
git add scripts/lista_maprex_usd.py tests/unit/test_lista_maprex_usd.py data/precios/maprex_2026-07/lista_maprex_usd.csv
git commit -m "feat(scripts): lista de precios maprex en usd en formato canonico"
```

---

## Task 7: Sembrar los rendimientos de la línea base

**Files:**
- Modify: `scripts/seed.py`
- Modify: `tests/integration/test_persistencia.py`

**Interfaces:**
- Consumes: `core.catalog.rendimientos.registrar_rendimiento(session, codigo_partida, valor, tipo, fecha, condiciones, referencia_ejecucion)`.
- Produces: cinco `Rendimiento` de tipo `ESTIMADO` en la base sembrada, para que
  `proponer_rendimiento` tenga qué proponer desde el primer uso de la página (fase P2).

- [ ] **Step 1: Escribir la prueba que falla**

El fixture `sesion` ya siembra la línea base, así que la prueba solo comprueba lo que la siembra
dejó. `CODIGOS` ya existe en el archivo (línea 22).

```python
def test_la_siembra_deja_rendimientos_estimados_con_condiciones(sesion):
    """Sin condiciones declaradas, un rendimiento estimado no tiene procedencia que auditar.

    La pagina de composicion (fase P2) exige declararlas; la siembra de la linea base tiene que
    dar el ejemplo, y ademas es lo que permite que proponer_rendimiento sugiera algo.
    """
    catalogo = Catalogo(sesion)

    for codigo in CODIGOS:
        registrados = catalogo.rendimientos(codigo)
        assert registrados, codigo
        assert all(rendimiento.condiciones for rendimiento in registrados), codigo
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/integration/test_persistencia.py -k siembra -v`
Expected: FAIL en el `assert all(r.condiciones ...)`, porque `cargar_composicion` registra el
rendimiento sin condiciones.

- [ ] **Step 3: Declarar las condiciones en el seed**

En `scripts/seed.py`, un diccionario de módulo con la condición declarada de cada partida, y tras
cargar cada composición, `registrar_rendimiento` con `TipoRendimiento.ESTIMADO`, la fecha de la línea
base y su condición. Las condiciones describen el supuesto, por ejemplo: *«cuadrilla de cinco
obreros, terreno sin roca, excavación manual»*. Documenta en el docstring del diccionario que son
**supuestos declarados del caso didáctico**, no mediciones de obra ejecutada.

- [ ] **Step 4: Ejecutar la prueba**

Run: `uv run pytest tests/integration/test_persistencia.py -k siembra -v`
Expected: 1 passed.

- [ ] **Step 5: Regenerar la base y comprobar la propuesta**

```bash
rm -f data/apu.db
uv run python scripts/seed.py
uv run python -c "from core.catalog import abrir_sesion, crear_motor; from core.catalog.rendimientos import proponer_rendimiento; m = crear_motor('sqlite:///data/apu.db'); s = next(iter([abrir_sesion(m).__enter__()])); print(proponer_rendimiento(s, 'LB-01-EXC'))"
```
Expected: una `PropuestaRendimiento` o `None` si hay una sola observación — ambas son correctas; lo
que no puede pasar es un error.

- [ ] **Step 6: Suite completa y cierre de fase**

Run: `uv run pytest -q && uv run ruff check . && uv run python scripts/meta_prototipo.py --hasta P1`
Expected: todo verde y las metas P4, P5 y P6 en OK.

- [ ] **Step 7: Commit**

```bash
git add scripts/seed.py tests/integration/test_persistencia.py
git commit -m "feat(scripts): siembra de los rendimientos estimados de la linea base"
```

---

## Cierre de las fases P0 y P1

Antes de abrir la fase P2, todo esto debe ser cierto:

```bash
uv run pytest -q                                      # todo verde
uv run ruff check .                                   # All checks passed!
uv run python scripts/guardia_nucleo.py --base p-base # OK
uv run python scripts/meta_prototipo.py --hasta P1    # metas P1 a P6 en OK
uv run python scripts/meta_datos.py                   # 3/3
git status --short tests/unit/test_costing.py tests/fixtures/apu_linea_base.py   # vacío
```

El último comando es el que importa más: si esos dos archivos aparecen modificados, la línea base se
tocó y el sprint se detiene.
