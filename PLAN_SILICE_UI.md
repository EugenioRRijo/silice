# Plan de construcción de la interfaz de trabajo de Sílice 1.0.0

> **Para quien ejecute (agentes):** SUB-SKILL REQUERIDA: `superpowers:subagent-driven-development`
> (un subagente por tarea con su ficha de rol `C:\Users\euger\.claude\agents\sf-ingeniero-interfaz.md`
> y un revisor fresco por tarea). Los pasos usan casillas `- [ ]`. **Sin pruebas nuevas ni `pytest`
> local** (RU-1): cada tarea cierra con `ruff`, su revisión manual en el navegador y su commit; la CI
> corre las pruebas existentes.

**Objetivo:** dar a Sílice 1.0.0 una interfaz de trabajo al estilo de los programas de presupuestos
de obra (ProEst, Procore, CostOS, PlanSwift) **con las herramientas que el repositorio ya tiene**:
un **tablero del proyecto** con tarjetas, anillos de progreso, curva de plan y avance, desglose del
costo, partidas principales y comparativo de versiones; una **línea de estado** en la barra
superior (proyecto, versión, estado y total); y la pestaña **APU de la hoja en tres paneles**
(partidas a la izquierda, tabla del APU por rubro al centro y cierre de la partida con sus factores
a la derecha).

**Arquitectura:** sin cambios en `core/`, `adapters/`, `api/` ni en la base de datos. Se sigue el
patrón de `ui/`: la lógica vive en módulos **sin Streamlit** (`ui/estilo.py`, `ui/tablero.py`) y
las pantallas solo pintan. Los gráficos se arman en `ui/graficos.py` con **Altair** (ya llega con
Streamlit y aquí se declara). El estilo visual sale del tema de `.streamlit/config.toml` y de
contenedores con borde, **sin CSS ni HTML sin escapar**. El tablero es de solo lectura: lee la
versión vigente con `core.budget.persistencia.cargar_elaboracion`, que no escribe.

**Tecnología:** Python 3.13, Streamlit ≥ 1.62 (extra `ui`), Altair ≥ 6 (extra `ui`), SQLAlchemy;
`Decimal` en todo monto (un `float` solo para dibujar).

**Spec:** este plan no tiene spec propio. Se apoya en los specs **aprobados** de Sílice
(`docs/especificaciones/2026-10-11-silice-1.0.0-design.md`, S2 §5.5 «Control de obra», S3 §5.7) y
en el spec del sprint SF (`2026-10-04-sprint-final-prototipo-design.md`, §5.3, §9 y §10: hoja y
barra). El encargo de Eugenio del 2026-10-12, con dos imágenes de tableros y dos maquetas pegadas,
es la referencia visual (§0.1).

---

## 0. Encargo, referencias y decisiones

### 0.1 Lo que pidió Eugenio (2026-10-12)

1. Un plan para construir la interfaz de la 1.0.0 tomando como ejemplo ProEst, Procore, CostOS y
   PlanSwift, y dos imágenes:
   - un tablero comparativo de datos operativos (tabla por meses, barras, línea y anillos);
   - un tablero de costos de obra (tarjetas de contrato, anillos de avance, SPI e índice de
     precios, curva programado / ejecutado / costo real y anillo de desglose del costo).
2. Una maqueta de **barra superior** («Proyecto · Estado · Total · [Exportar] [Guardar]») y de **tres
   paneles**: árbol de partidas, tabla del APU por recursos y un resumen fijo de costos.
3. Una lista de ingredientes: filas agrupadas por rubro (materiales, mano de obra, equipos y
   transporte), edición en línea con recálculo inmediato, selector con autocompletado del catálogo
   y un panel lateral de factores (FCAS, administración, imprevistos y utilidad) con el cierre paso
   a paso del costo directo al precio unitario.
4. «Son algunos de los ingredientes, que pueden o no estar según nuestro trabajo; adapta lo visual
   y construye según las herramientas que tenemos.»

### 0.2 Qué se toma, qué se adapta y qué queda fuera

| Ingrediente | Decisión | Por qué |
|---|---|---|
| Tarjetas de contrato, anillos de avance, SPI y CPI | **Se toma** (tarea 4) | `ui.control` (0.7.0) entrega `Indicadores` con PV, EV, AC, SPI, CPI y EAC |
| Curva programado / ejecutado / costo real | **Se toma** como PV / EV / AC (tarea 4) | `ui.control.curva_pv_ev_ac` |
| Anillo de desglose del costo | **Se toma**: materiales, equipos, mano de obra, administración y utilidad (tarea 2) | `ResultadoAPU` de cada renglón; suman exactamente el total |
| Tabla comparativa con barras | **Se adapta**: comparativo de las **versiones** del proyecto (tarea 2) | No hay meses ni «ingresos y gastos»; sí hay un historial de versiones |
| Barra superior con estado y total | **Se adapta**: línea de estado bajo la barra que ya existe (tarea 5) | Proyecto, Guardar y Exportar ya están en `ui/barra.py` (SF4) |
| Árbol de partidas | **Se adapta**: lista filtrable de las partidas valoradas (tarea 6) | El modelo **no tiene capítulos** (RU-6) |
| Tabla del APU agrupada por rubro, editable en línea | **Se toma** con tres rubros (tarea 6) | Ya hay un editor por rubro; no existe el rubro transporte (RU-4) |
| Recálculo «al instante en el frontend» | **Se adapta**: el recálculo es en el servidor, en cada edición (RU-5) | Streamlit no corre la lógica en el navegador |
| Selector con autocompletado | **Se toma** (tarea 6) | `st.selectbox` filtra al escribir sobre `hoja.insumos_candidatos` |
| Panel de factores con el cierre paso a paso | **Se toma** con FCAS, bono, administración y utilidad (tarea 6) | `ParametrosCosto` y la cascada de `core.costing.motor.calcular_apu` |
| Imprevistos | **Fuera** (RU-3) | No existe en `ParametrosCosto`; agregarlo toca `core/` |
| Sliders | **Se reemplazan** por campos de texto exactos (RU-7) | Un slider devuelve `float` y el sistema exige `Decimal` |
| Panel «fijo» con CSS (`position: sticky`) | **Fuera** (RU-8) | `ui/barra.py` ya lo descartó: exige HTML sin escapar |

### 0.3 Rulings de este plan

| # | Ruling | Si resulta erróneo |
|---|---|---|
| RU-1 | Sin pruebas nuevas ni `pytest` local, por la instrucción de Eugenio del 2026-10-12. Cada tarea cierra con `ruff check`/`ruff format` sobre lo que toca y una revisión manual en el navegador. La CI corre las pruebas existentes, y si alguna se pone roja se arregla el código. Lo que queda sin prueba se anota en la bitácora (tarea 7) para la auditoría final | Las pruebas se escriben en la auditoría final |
| RU-2 | **Agregar la página Tablero cambia tres enumeraciones de pruebas existentes**: 14 → 15 páginas en `test_ui_importable.py`, el título nuevo en `TITULOS_TRABAJO` de `test_ui_app.py` y `"tablero"` en `PAGINAS_QUE_ABREN_EL_CASO` de `test_arquitectura_s5.py`. Se actualizan como **datos** de la lista, sin debilitar ninguna aserción. **Pide la ratificación de Eugenio**, porque toca pruebas existentes | Sin ratificación, el tablero no se registra en el menú y la tarea 4 se detiene en su paso 4 |
| RU-3 | Imprevistos fuera: el panel muestra FCAS, bono, administración y utilidad. Agregar imprevistos es un expediente de `core/` (contrato, motor, persistencia y Alembic), fuera de este plan | Plan aparte con expediente, si Eugenio lo pide |
| RU-4 | Sin rubro de transporte: hoy un flete entra como material o como equipo. No se inventa un cuarto grupo en la pantalla | Mismo camino que RU-3 |
| RU-5 | «Recálculo inmediato» significa que cada edición vuelve a ejecutar la pestaña y recalcula en el servidor con `ui.hoja.elaborar_borrador`, como hoy. No se usa `st.fragment`: el panel de guardado se llena al final de `render()` y debe ver los cambios de la misma ejecución | Medir con `scripts/medir_rnf11.py`; ajustar después |
| RU-6 | Sin árbol: el modelo no tiene capítulos ni jerarquía de partidas. La columna izquierda es una lista de las partidas valoradas con buscador (código o descripción, sin acentos) | Los capítulos serían un expediente de `core/` |
| RU-7 | Los factores se editan con `st.text_input` y se leen con `hoja.parametros_desde_texto`, igual que la pestaña Parámetros y con el mismo código (DRY) | — |
| RU-8 | Sin CSS ni `unsafe_allow_html`. El estilo sale de `[theme]` en `.streamlit/config.toml` y de `st.container(border=True)` y `st.metric(border=True)` | — |
| RU-9 | Texto ajeno (nombre del proyecto, código de versión, descripciones de partidas e insumos, motivos de error) **nunca** va crudo en `st.markdown`, `st.caption`, `st.info`, en etiquetas ni en opciones de `st.radio`: pasa por `ui.texto_seguro.texto_seguro`, o va en celdas de tabla y tooltips de Altair, que son texto plano. Las etiquetas de `st.metric` solo llevan textos propios del sistema | — |
| RU-10 | El tablero es de solo lectura: `cargar_elaboracion` reconstruye la versión vigente sin escribir. **No** usa `hoja.abrir_version`, que registra la instantánea | — |
| RU-11 | Altair se declara en el extra `ui` (`altair>=6`); hoy llega transitivo con Streamlit (6.2.2 en `uv.lock`) | — |
| RU-12 | Con control de obra, la curva del tablero muestra PV, EV y AC y **no** la curva del plan: PV es el plan en la perspectiva de la línea base (costo o precio) y mezclar ambas escalas confundiría. Sin control, muestra el plan acumulado del presupuesto | — |

### 0.4 Hallazgo fuera de alcance (para la auditoría final)

`ui/barra.py` interpola el nombre del proyecto sin `texto_seguro` en dos `st.markdown`
(`_pintar_proyecto` y la línea «Proyecto abierto: **…**»), y `ui/resultado.py::_pendientes` hace lo
mismo con descripciones. Este plan **no** los toca: `test_ui_barra.py:427` exige el texto literal y
cambiarlo es otra decisión. Se anota en la bitácora (tarea 7).

### 0.5 Requisito previo

La tarea 2 importa `ui.control`, que entra a `main` con la **tarea 13 del plan de la 0.7.0**
(pantalla «Control de obra», rama `inc/070-s2-4-ui`). Antes de empezar:

```bash
git fetch origin && git show origin/main:ui/control.py > /dev/null && echo "ui.control en main"
```

Si no imprime `ui.control en main`, se esperan esa fusión y la tarea 1, que no depende de ella,
puede ir antes.

## Restricciones globales

- `core/`, `adapters/`, `api/`, `migraciones/` y la base: **sin cambios**.
- `ui/estilo.py` y `ui/tablero.py`: **sin `streamlit` ni `pandas`**. `ui/graficos.py`: sin `streamlit` ni `pandas`.
- Las páginas exponen `def render() -> None` sin efectos al importarse y exigen su acción con `ui_sesion.exigir(...)`.
- Solo `ui/app.py` importa `ui.barra`, y ninguna página importa `ui.app`.
- Las celdas de `st.data_editor` se leen solo con `ui.composicion.texto_de_celda`.
- Montos en `Decimal`; el `float` aparece solo en los datos que recibe un gráfico.
- La tupla `PESTANAS` de la hoja **no cambia**. La pestaña APU conserva la métrica «Precio unitario» y al menos tres tablas (`test_ui_hoja.py:229`).
- La opción de radio, la etiqueta y el texto de ayuda nunca llevan texto ajeno sin `texto_seguro` (RU-9).
- Comandos: `uv run --extra ui ruff check <archivos>` y `uv run --extra ui ruff format <archivos>`.
- Rama `inc/silice-ui` desde `origin/main` y un solo PR al final (tarea 7).
- Commits con la línea `Co-Authored-By` que indique el sistema.

## Foco de la revisión

1. **Proyecto sin versión guardada o caso vacío:** el tablero dice qué hacer («ármelo en la Hoja del proyecto») y no rompe. Tarea 4, paso 3.
2. **Presupuesto con total cero o sin curva:** sin división por cero; el anillo y el Pareto quedan vacíos con un aviso. Tarea 2 (`if total == CERO`).
3. **Control de obra no disponible** (sin línea base, sin valuaciones o `ControlInvalido` por cambio de moneda): el tablero muestra el motivo escapado y sigue con el resto. Tarea 2 (`leer_control`) y tarea 4.
4. **Filtro de partidas que no deja ninguna**, o una partida elegida que desaparece del filtro: la lista vuelve a mostrar todas y el radio no queda con un valor inválido. Tarea 6, paso 2.
5. **Nombre de proyecto o descripción con `*`, `_`, `[`, `<` o `#`:** se muestra literal, sin formato ni enlaces. Tareas 4, 5 y 6 (RU-9).

---

## Mapa de archivos

| Archivo | Tarea | Responsabilidad |
|---|---|---|
| `.streamlit/config.toml` | 1 | sección `[theme]` |
| `pyproject.toml`, `uv.lock` | 1 | `altair>=6` en el extra `ui` |
| `ui/estilo.py` (nuevo) | 1 | paleta y formatos (dinero, porcentaje, índice); sin Streamlit |
| `ui/tablero.py` (nuevo) | 2 | lectura de la versión vigente y del control; filas y tarjetas del tablero; sin Streamlit |
| `ui/graficos.py` (nuevo) | 3 | gráficos Altair: anillo, desglose, curvas, Pareto y versiones |
| `ui/paginas/tablero.py` (nuevo) | 4 | la pantalla «Tablero del proyecto» |
| `ui/app.py` | 4, 5 | registro de la página; hueco de la línea de estado en `marco()` |
| `tests/unit/test_ui_importable.py`, `test_ui_app.py`, `test_arquitectura_s5.py` | 4 | enumeraciones (RU-2) |
| `ui/caso.py` | 5 | `ResumenDeTrabajo`, `publicar_resumen`, `resumen_publicado` |
| `ui/barra.py` | 5 | `pintar_estado()` |
| `ui/hoja.py` | 6 | `filtrar_partidas`, `filas_de_cierre` |
| `ui/paginas/hoja.py` | 5, 6 | publica el resumen; pestaña APU en tres paneles; parámetros compartidos |
| `NORMAS.md` §6, `docs/manual_usuario.md`, `CHANGELOG.md`, `docs/bitacora/2026-10-12-interfaz-de-trabajo.md` | 7 | documentos |

---

### Tarea 1: Tema visual, paleta y Altair declarado

**Files:**
- Modify: `.streamlit/config.toml` (agregar `[theme]` al final)
- Modify: `pyproject.toml:27` (extra `ui`), `uv.lock` (lo regenera `uv lock`)
- Create: `ui/estilo.py`

**Interfaces:**
- Produce: `ui.estilo.COLOR_PRIMARIO`, `COLOR_TENUE`, `COLOR_BIEN`, `COLOR_ATENCION`, `COLORES_RUBRO: dict[str, str]`, `COLORES_SERIE: dict[str, str]`, `NO_DISPONIBLE`, `dinero(valor: Decimal | None, moneda: str) -> str`, `porcentaje(fraccion: Decimal | None) -> str`, `indice(valor: Decimal | None) -> str`.

- [ ] **Paso 1: Agregar el tema al final de `.streamlit/config.toml`**

```toml

[theme]
# Interfaz de trabajo (PLAN_SILICE_UI, tarea 1). Los mismos valores que ui/estilo.py (una copia
# por formato: Streamlit no lee Python). Sin CSS (RU-8).
base = "light"
primaryColor = "#1F4E79"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F3F5F8"
textColor = "#1B1F24"
borderColor = "#D5DAE1"
showWidgetBorder = true
baseRadius = "small"
font = "sans-serif"
```

- [ ] **Paso 2: Comprobar que Streamlit conoce cada opción** (la CI lo exige en `test_streamlit_conoce_cada_opcion_del_archivo`; esto no es `pytest`, solo lee la lista de opciones)

Run:
```bash
uv run --extra ui python -c "import tomllib; from streamlit import config as c; o=c.get_config_options(); t=tomllib.load(open('.streamlit/config.toml','rb'))['theme']; print([k for k in t if f'theme.{k}' not in o])"
```
Expected: `[]`. Si aparece alguna, se quita esa línea del `[theme]`; no se reemplaza por CSS.

- [ ] **Paso 3: Declarar Altair en el extra `ui`**

En `pyproject.toml`, la línea 27:

```toml
ui = ["streamlit>=1.62", "altair>=6"]
```

Run: `uv lock`
Expected: `uv.lock` cambia solo en la declaración del extra (`altair` ya está fijado en 6.2.2).

- [ ] **Paso 4: Crear `ui/estilo.py`**

```python
"""Paleta y formatos de la interfaz de trabajo (PLAN_SILICE_UI, tarea 1). Sin Streamlit.

Una sola copia de los colores para los graficos (`ui.graficos`) y las pantallas. El tema de
`.streamlit/config.toml` repite `COLOR_PRIMARIO` y los fondos porque Streamlit no lee Python.

Los formatos devuelven texto para mostrar; el monto sigue siendo `Decimal` hasta aqui.
"""

from __future__ import annotations

from decimal import Decimal

from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

COLOR_PRIMARIO = "#1F4E79"
COLOR_TENUE = "#E6E9EE"
COLOR_BIEN = "#2E7D5B"
COLOR_ATENCION = "#D9A441"

COLORES_RUBRO: dict[str, str] = {
    "Materiales": "#1F4E79",
    "Equipos": "#5B8DB8",
    "Mano de obra": "#D9A441",
    "Administracion": "#7A7F87",
    "Utilidad": "#2E7D5B",
}
COLORES_SERIE: dict[str, str] = {
    "Plan": "#1F4E79",
    "PV": "#7A7F87",
    "EV": "#D9A441",
    "AC": "#B5443A",
}

NO_DISPONIBLE = "no disponible"


def dinero(valor: Decimal | None, moneda: str) -> str:
    """Un monto con los decimales de presentacion y su moneda; `None` es «no disponible»."""
    if valor is None:
        return NO_DISPONIBLE
    return f"{formatear_decimal(valor, DECIMALES_PRESENTACION)} {moneda}"


def porcentaje(fraccion: Decimal | None) -> str:
    """Una fraccion (0.15) como porcentaje con un decimal (15.0 %)."""
    if fraccion is None:
        return NO_DISPONIBLE
    return f"{formatear_decimal(fraccion * 100, 1)} %"


def indice(valor: Decimal | None) -> str:
    """Un indice (SPI, CPI) con dos decimales."""
    if valor is None:
        return NO_DISPONIBLE
    return formatear_decimal(valor, 2)
```

- [ ] **Paso 5: ruff**

Run: `uv run --extra ui ruff check ui/estilo.py && uv run --extra ui ruff format ui/estilo.py`
Expected: sin hallazgos.

- [ ] **Paso 6: Revisión en el navegador**

Run: `uv run --extra ui --extra api --extra civil python -m streamlit run ui/app.py`
Expected: la aplicación arranca con el azul `#1F4E79` en botones y selección, y los bordes visibles en los campos. Nada más cambia.

- [ ] **Paso 7: Commit**

```bash
git add .streamlit/config.toml pyproject.toml uv.lock ui/estilo.py
git commit -m "feat(ui): tema visual, paleta de la interfaz y altair declarado en el extra ui"
```

---

### Tarea 2: `ui/tablero.py`, los datos del tablero sin Streamlit

**Files:**
- Create: `ui/tablero.py`

**Interfaces:**
- Consume: `ui.estilo.dinero`, `porcentaje`, `indice`, `NO_DISPONIBLE` (tarea 1). `ui.control.tiene_linea_base(sesion, proyecto) -> bool`, `hay_valuaciones(sesion, proyecto) -> bool`, `corte_por_defecto(sesion, proyecto) -> date`, `calcular_el_control(sesion, proyecto, catalogo, *, corte) -> ResultadoControl`, `curva_pv_ev_ac(sesion, resultado) -> list[dict[str, object]]` y `ControlInvalido` (0.7.0). `ui.hoja.codigo_vigente(sesion, proyecto) -> str | None` y `ui.hoja.historial_de_versiones(sesion, proyecto) -> list[FilaVersion]`. `core.budget.persistencia.cargar_elaboracion(session, proyecto_nombre, codigo, catalogo) -> ResultadoElaboracion` y `core.budget.equilibrio.punto_equilibrio(presupuesto, parametros) -> PuntoEquilibrio`.
- Produce:
  - `Tarjeta(rotulo: str, valor: str, detalle: str = "")`
  - `DatosControl(indicadores: Indicadores | None, curva: list[dict[str, object]], motivo: str)`
  - `DatosTablero(proyecto, codigo, fecha, elaboracion, equilibrio, versiones, control)`
  - `leer_tablero(sesion, catalogo, proyecto) -> DatosTablero | None`
  - `tarjetas_del_presupuesto(datos) -> list[Tarjeta]`
  - `tarjetas_de_control(control, moneda) -> list[Tarjeta]`
  - `filas_de_desglose(presupuesto) -> list[dict[str, object]]`
  - `filas_pareto(presupuesto, n=10) -> list[dict[str, object]]`
  - `filas_de_curvas(presupuesto, control) -> list[dict[str, object]]`
  - `avance_fisico(indicadores) -> Decimal | None`

- [ ] **Paso 1: Comprobar el requisito previo (§0.5)**

Run: `git fetch origin && git show origin/main:ui/control.py > /dev/null && echo "ui.control en main"`
Expected: `ui.control en main`. Si no aparece, la tarea se detiene y lo dice.

- [ ] **Paso 2: Crear `ui/tablero.py`**

```python
"""Datos del tablero del proyecto, sin Streamlit ni pandas (PLAN_SILICE_UI, tarea 2).

El tablero es de **solo lectura** (RU-10): lee la version vigente con
`core.budget.persistencia.cargar_elaboracion`, que reconstruye el presupuesto y su informe sin
escribir, y el control de obra con `ui.control` (0.7.0). Aqui solo se arman filas y tarjetas; la
pantalla `ui/paginas/tablero.py` las pinta y `ui/graficos.py` las dibuja.

Las filas para graficos llevan una columna `float` (`monto`, `Acumulado`) solo para dibujar; el
texto que se muestra sale del `Decimal` con `ui.estilo`. Las etiquetas de `Tarjeta.rotulo` son
textos del sistema: van a la etiqueta de `st.metric`, que interpreta Markdown (RU-9).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.equilibrio import PuntoEquilibrio, punto_equilibrio
from core.budget.persistencia import cargar_elaboracion
from core.budget.presupuesto import ResultadoElaboracion
from core.budget.valor_ganado import Indicadores
from core.catalog import Catalogo
from core.contracts import ParametrosCosto, Severidad
from core.contracts.presupuesto import Presupuesto
from core.verification.texto import formatear_decimal
from ui import control, hoja
from ui.estilo import NO_DISPONIBLE, dinero, indice, porcentaje

CERO = Decimal(0)
PARTIDAS_EN_PARETO = 10


@dataclass(frozen=True, slots=True)
class Tarjeta:
    """Una tarjeta del tablero: etiqueta del sistema, valor y una ayuda opcional."""

    rotulo: str
    valor: str
    detalle: str = ""


@dataclass(frozen=True, slots=True)
class DatosControl:
    """El control de obra al ultimo corte, o el motivo por el que no hay (`indicadores` None)."""

    indicadores: Indicadores | None
    curva: list[dict[str, object]]
    motivo: str


@dataclass(frozen=True, slots=True)
class DatosTablero:
    """Todo lo que pinta el tablero, leido en una sola sesion."""

    proyecto: str
    codigo: str
    fecha: date
    elaboracion: ResultadoElaboracion
    equilibrio: PuntoEquilibrio
    versiones: list[dict[str, object]]
    control: DatosControl


# --- lectura -------------------------------------------------------------------------------------


def _version(sesion: Session, proyecto: str, codigo: str) -> models.Presupuesto:
    return sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one()


def leer_tablero(sesion: Session, catalogo: Catalogo, proyecto: str) -> DatosTablero | None:
    """El tablero de la version vigente del proyecto; `None` si no tiene version guardada.

    `ValueError` si el catalogo ya no reconstruye la version (`cargar_presupuesto`): la pantalla
    lo muestra y no pinta cifras.
    """
    codigo = hoja.codigo_vigente(sesion, proyecto)
    if codigo is None:
        return None
    modelo = _version(sesion, proyecto, codigo)
    elaboracion = cargar_elaboracion(sesion, proyecto, codigo, catalogo)
    parametros = ParametrosCosto(
        fcas=modelo.fcas,
        bono_alimentacion=modelo.bono_alimentacion,
        administracion=modelo.administracion,
        utilidad=modelo.utilidad,
    )
    return DatosTablero(
        proyecto=proyecto,
        codigo=codigo,
        fecha=modelo.fecha,
        elaboracion=elaboracion,
        equilibrio=punto_equilibrio(elaboracion.presupuesto, parametros),
        versiones=filas_comparativo(sesion, proyecto),
        control=leer_control(sesion, catalogo, proyecto),
    )


def leer_control(sesion: Session, catalogo: Catalogo, proyecto: str) -> DatosControl:
    """El control al corte por defecto (la ultima valuacion), sin escribir."""
    if not control.tiene_linea_base(sesion, proyecto):
        return DatosControl(None, [], "Sin linea base de control: declarela en Control de obra.")
    if not control.hay_valuaciones(sesion, proyecto):
        return DatosControl(None, [], "La linea base esta declarada; falta la primera valuacion.")
    try:
        resultado = control.calcular_el_control(
            sesion, proyecto, catalogo, corte=control.corte_por_defecto(sesion, proyecto)
        )
    except control.ControlInvalido as error:
        return DatosControl(None, [], str(error))
    return DatosControl(resultado.indicadores, control.curva_pv_ev_ac(sesion, resultado), "")


def filas_comparativo(sesion: Session, proyecto: str) -> list[dict[str, object]]:
    """Una fila por version no descartada, de la mas antigua a la mas reciente.

    Los totales salen de las filas guardadas (`partida_presupuestada.total`), sumados en Python
    con `Decimal`: no se recalcula nada.
    """
    filas: list[dict[str, object]] = []
    for version in hoja.historial_de_versiones(sesion, proyecto):
        if version.descartada:
            continue
        modelo = _version(sesion, proyecto, version.codigo)
        total = sum((r.total for r in modelo.partidas), CERO)
        directo = sum((r.cantidad * r.costo_directo for r in modelo.partidas), CERO)
        filas.append(
            {
                "Version": version.codigo,
                "Fecha": version.fecha.isoformat(),
                "Motivo": version.motivo or "elaborada",
                "Costo directo": dinero(directo, modelo.moneda),
                "Total": dinero(total, modelo.moneda),
                "Vigente": "si" if version.vigente else "",
                "total": float(total),
            }
        )
    return filas


# --- tarjetas ------------------------------------------------------------------------------------


def _costo_directo(presupuesto: Presupuesto) -> Decimal:
    return sum((p.item.cantidad * p.resultado.costo_directo for p in presupuesto.partidas), CERO)


def tarjetas_del_presupuesto(datos: DatosTablero) -> list[Tarjeta]:
    """Total, costo directo, punto de equilibrio y auditoria de la version vigente."""
    presupuesto = datos.elaboracion.presupuesto
    moneda = presupuesto.moneda
    pe = datos.equilibrio
    informe = datos.elaboracion.informe
    cuenta = Counter(h.severidad for h in informe.hallazgos)
    detalle = ", ".join(f"{cuenta[s]} {s.name.lower()}" for s in reversed(Severidad) if cuenta[s])
    return [
        Tarjeta("Total del contrato", dinero(presupuesto.total, moneda)),
        Tarjeta("Costo directo", dinero(_costo_directo(presupuesto), moneda)),
        Tarjeta(
            "Punto de equilibrio",
            NO_DISPONIBLE if pe.porcentaje is None else f"{formatear_decimal(pe.porcentaje, 2)} %",
            pe.mensaje,
        ),
        Tarjeta(
            "Auditoria",
            "CUMPLE" if informe.cumple else "NO CUMPLE",
            detalle or "sin hallazgos",
        ),
    ]


def avance_fisico(indicadores: Indicadores | None) -> Decimal | None:
    """EV / BAC, la fraccion ganada del presupuesto; `None` sin control o con BAC cero."""
    if indicadores is None or indicadores.bac == CERO:
        return None
    return indicadores.ev / indicadores.bac


def tarjetas_de_control(datos: DatosControl, moneda: str) -> list[Tarjeta]:
    """Avance fisico, SPI, CPI y EAC al corte; cada «no disponible» con su motivo."""
    ind = datos.indicadores
    if ind is None:
        return []
    motivo = ind.no_disponible
    return [
        Tarjeta("Avance fisico (EV/BAC)", porcentaje(avance_fisico(ind))),
        Tarjeta("SPI (plazo)", indice(ind.spi), motivo.get("spi", "")),
        Tarjeta("CPI (costo)", indice(ind.cpi), motivo.get("cpi", "")),
        Tarjeta("EAC (costo final estimado)", dinero(ind.eac_indice, moneda), motivo.get("eac_indice", "")),
    ]


# --- filas para graficos -------------------------------------------------------------------------


def filas_de_desglose(presupuesto: Presupuesto) -> list[dict[str, object]]:
    """El total del contrato por rubro. Los cinco suman exactamente `presupuesto.total`.

    Administracion = cantidad x (con_administracion - costo_directo); utilidad = cantidad x
    (precio_unitario - con_administracion), la cascada de `core.costing.motor.calcular_apu`.
    Lista vacia si el total es cero.
    """
    montos = dict.fromkeys(("Materiales", "Equipos", "Mano de obra", "Administracion", "Utilidad"), CERO)
    for partida in presupuesto.partidas:
        q, r = partida.item.cantidad, partida.resultado
        montos["Materiales"] += q * r.materiales
        montos["Equipos"] += q * r.equipos
        montos["Mano de obra"] += q * r.mano_obra
        montos["Administracion"] += q * (r.con_administracion - r.costo_directo)
        montos["Utilidad"] += q * (r.precio_unitario - r.con_administracion)
    total = presupuesto.total
    if total == CERO:
        return []
    return [
        {
            "Rubro": rubro,
            "Monto": dinero(monto, presupuesto.moneda),
            "Peso": porcentaje(monto / total),
            "monto": float(monto),
        }
        for rubro, monto in montos.items()
    ]


def filas_pareto(presupuesto: Presupuesto, n: int = PARTIDAS_EN_PARETO) -> list[dict[str, object]]:
    """Las `n` partidas de mayor total (sumando sus renglones), con su peso y el acumulado, y una
    fila «Resto» si hay mas. Lista vacia si el total es cero."""
    total = presupuesto.total
    if total == CERO:
        return []
    por_partida: dict[str, tuple[str, Decimal]] = {}
    for partida in presupuesto.partidas:
        codigo = partida.item.codigo_partida
        descripcion, monto = por_partida.get(codigo, (partida.apu.descripcion, CERO))
        por_partida[codigo] = (descripcion, monto + partida.total)
    orden = sorted(por_partida.items(), key=lambda par: (-par[1][1], par[0]))
    filas: list[dict[str, object]] = []
    acumulado = CERO
    for codigo, (descripcion, monto) in orden[:n]:
        acumulado += monto
        filas.append(
            {
                "Partida": codigo,
                "Descripcion": descripcion,
                "Total": dinero(monto, presupuesto.moneda),
                "Peso": porcentaje(monto / total),
                "Acumulado": porcentaje(acumulado / total),
                "monto": float(monto),
            }
        )
    if len(orden) > n:
        resto = total - acumulado
        filas.append(
            {
                "Partida": f"Resto ({len(orden) - n})",
                "Descripcion": "las demas partidas",
                "Total": dinero(resto, presupuesto.moneda),
                "Peso": porcentaje(resto / total),
                "Acumulado": porcentaje(Decimal(1)),
                "monto": float(resto),
            }
        )
    return filas


def filas_de_curvas(presupuesto: Presupuesto, control_obra: DatosControl) -> list[dict[str, object]]:
    """Filas largas (Orden, Periodo, Serie, Acumulado) para la curva del tablero.

    Con control: PV, EV y AC acumulados al cierre de cada periodo (el AC falta donde un costo no
    tiene tasa). Sin control: el plan acumulado del presupuesto (RU-12).
    """
    if control_obra.indicadores is not None:
        filas = []
        for orden, punto in enumerate(control_obra.curva, start=1):
            for serie in ("PV", "EV", "AC"):
                valor = punto[serie]
                if valor is not None:
                    filas.append(
                        {
                            "Orden": orden,
                            "Periodo": str(punto["Periodo"]),
                            "Serie": serie,
                            "Acumulado": float(valor),
                        }
                    )
        return filas
    return [
        {"Orden": orden, "Periodo": p.periodo, "Serie": "Plan", "Acumulado": float(p.acumulado)}
        for orden, p in enumerate(presupuesto.curva, start=1)
    ]
```

- [ ] **Paso 3: ruff**

Run: `uv run --extra ui ruff check ui/tablero.py && uv run --extra ui ruff format ui/tablero.py`
Expected: sin hallazgos. Las líneas largas que separe `ruff format` se aceptan como quedan.

- [ ] **Paso 4: Comprobar a mano con el caso de demostración** (sin `pytest`: un script de una línea)

Run:
```bash
uv run --extra ui python -c "
from pathlib import Path; from core.catalog import Catalogo, abrir_sesion, crear_motor
from ui import tablero; from ui.caso import ruta_caso
r=ruta_caso(); m=crear_motor(f'sqlite:///{r.as_posix()}')
with abrir_sesion(m) as s:
    from ui.proyectos import listar_proyectos
    for p in listar_proyectos(r):
        d=tablero.leer_tablero(s, Catalogo(s), p)
        print(p, None if d is None else ([t.valor for t in tablero.tarjetas_del_presupuesto(d)], sum(f['monto'] for f in tablero.filas_de_desglose(d.elaboracion.presupuesto)), float(d.elaboracion.presupuesto.total)))
"
```
Expected: en cada proyecto con versión, la suma de `monto` del desglose coincide con el total (diferencia menor que 0,01). Si el caso no tiene proyectos, se carga la demostración desde Inicio y se repite.

- [ ] **Paso 5: Commit**

```bash
git add ui/tablero.py
git commit -m "feat(ui): datos del tablero del proyecto sin streamlit (version vigente, control, desglose, pareto)"
```

---

### Tarea 3: `ui/graficos.py`, los gráficos en Altair

**Files:**
- Create: `ui/graficos.py`

**Interfaces:**
- Consume: las filas de la tarea 2 y la paleta de la tarea 1.
- Produce:
  - `anillo(fraccion: float, texto: str, *, color: str = COLOR_PRIMARIO) -> alt.LayerChart`
  - `desglose(filas) -> alt.Chart`
  - `curvas(filas) -> alt.Chart`
  - `pareto(filas) -> alt.Chart`
  - `versiones(filas) -> alt.Chart`

- [ ] **Paso 1: Crear `ui/graficos.py`**

```python
"""Graficos del tablero en Altair, sin Streamlit ni pandas (PLAN_SILICE_UI, tarea 3).

Cada funcion recibe las filas de `ui.tablero` (dicts) y devuelve un grafico de Altair con los
datos en linea (`alt.Data(values=...)`), sin DataFrame. La pantalla los pinta con
`st.altair_chart`. Los tooltips de Vega-Lite son texto plano: las descripciones ajenas van ahi,
nunca en un titulo (RU-9).
"""

from __future__ import annotations

from collections.abc import Sequence

import altair as alt

from ui.estilo import COLOR_PRIMARIO, COLOR_TENUE, COLORES_RUBRO, COLORES_SERIE

Filas = Sequence[dict[str, object]]


def anillo(fraccion: float, texto: str, *, color: str = COLOR_PRIMARIO) -> alt.LayerChart:
    """Un anillo de progreso con `texto` al centro; la fraccion se recorta a [0, 1]."""
    parte = min(max(fraccion, 0.0), 1.0)
    arcos = (
        alt.Chart(alt.Data(values=[{"parte": "a", "valor": parte}, {"parte": "b", "valor": 1 - parte}]))
        .mark_arc(innerRadius=44, outerRadius=60)
        .encode(
            theta=alt.Theta("valor:Q", stack=True),
            color=alt.Color(
                "parte:N", scale=alt.Scale(domain=["a", "b"], range=[color, COLOR_TENUE]), legend=None
            ),
            order=alt.Order("parte:N"),
        )
    )
    centro = (
        alt.Chart(alt.Data(values=[{"t": texto}]))
        .mark_text(fontSize=18, fontWeight="bold")
        .encode(text="t:N")
    )
    return alt.layer(arcos, centro).properties(width=140, height=140)


def desglose(filas: Filas) -> alt.Chart:
    """Anillo del costo por rubro."""
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_arc(innerRadius=60)
        .encode(
            theta=alt.Theta("monto:Q"),
            color=alt.Color(
                "Rubro:N",
                scale=alt.Scale(domain=list(COLORES_RUBRO), range=list(COLORES_RUBRO.values())),
                legend=alt.Legend(orient="bottom", title=None),
            ),
            tooltip=["Rubro:N", "Monto:N", "Peso:N"],
        )
        .properties(height=280)
    )


def curvas(filas: Filas) -> alt.Chart:
    """Lineas acumuladas por periodo: Plan, o PV, EV y AC."""
    presentes = [s for s in COLORES_SERIE if any(f["Serie"] == s for f in filas)]
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_line(point=True)
        .encode(
            x=alt.X("Orden:O", title="Periodo"),
            y=alt.Y("Acumulado:Q", title="Acumulado"),
            color=alt.Color(
                "Serie:N",
                scale=alt.Scale(domain=presentes, range=[COLORES_SERIE[s] for s in presentes]),
                legend=alt.Legend(orient="top", title=None),
            ),
            tooltip=["Periodo:N", "Serie:N", alt.Tooltip("Acumulado:Q", format=",.2f")],
        )
        .properties(height=280)
    )


def pareto(filas: Filas) -> alt.Chart:
    """Barras horizontales de las partidas de mayor total."""
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_bar(color=COLOR_PRIMARIO)
        .encode(
            y=alt.Y("Partida:N", sort="-x", title=None),
            x=alt.X("monto:Q", title="Total"),
            tooltip=["Partida:N", "Descripcion:N", "Total:N", "Peso:N", "Acumulado:N"],
        )
        .properties(height=300)
    )


def versiones(filas: Filas) -> alt.Chart:
    """Total de cada version, la vigente resaltada."""
    return (
        alt.Chart(alt.Data(values=list(filas)))
        .mark_bar()
        .encode(
            x=alt.X("Version:N", sort=None, title=None),
            y=alt.Y("total:Q", title="Total"),
            color=alt.condition(
                alt.datum.Vigente == "si", alt.value(COLOR_PRIMARIO), alt.value(COLOR_TENUE)
            ),
            tooltip=["Version:N", "Fecha:N", "Motivo:N", "Total:N"],
        )
        .properties(height=240)
    )
```

- [ ] **Paso 2: ruff y una comprobación de que cada gráfico se serializa** (sin `pytest`)

Run:
```bash
uv run --extra ui ruff check ui/graficos.py && uv run --extra ui ruff format ui/graficos.py
uv run --extra ui python -c "
from ui import graficos as g
f=[{'Rubro':'Materiales','Monto':'1 USD','Peso':'50.0 %','monto':1.0},{'Rubro':'Utilidad','Monto':'1 USD','Peso':'50.0 %','monto':1.0}]
c=[{'Orden':1,'Periodo':'S1','Serie':'Plan','Acumulado':1.0}]
p=[{'Partida':'A','Descripcion':'d','Total':'1','Peso':'1','Acumulado':'1','monto':1.0}]
v=[{'Version':'001','Fecha':'2026-10-12','Motivo':'elaborada','Total':'1','Vigente':'si','total':1.0}]
for x in (g.anillo(0.4,'40 %'), g.desglose(f), g.curvas(c), g.pareto(p), g.versiones(v)): x.to_dict()
print('ok')"
```
Expected: `ok`.

- [ ] **Paso 3: Commit**

```bash
git add ui/graficos.py
git commit -m "feat(ui): graficos del tablero en altair (anillo, desglose, curvas, pareto y versiones)"
```

---

### Tarea 4: La pantalla «Tablero del proyecto» y su registro

**Files:**
- Create: `ui/paginas/tablero.py`
- Modify: `ui/app.py` (importar `tablero` en el bloque `from ui.paginas import (...)` y agregarlo a `PAGINAS` justo después de `PAGINA_INICIO`)
- Modify (RU-2, con ratificación): `tests/unit/test_ui_importable.py`, `tests/unit/test_ui_app.py`, `tests/unit/test_arquitectura_s5.py`

**Interfaces:**
- Consume: tareas 1, 2 y 3; `ui.caso.proyecto_abierto()`, `ui.caso.ruta_caso()`, `operacion.base_datos.preparar_base`, `core.catalog.crear_motor` y `abrir_sesion`, `ui.texto_seguro.texto_seguro`.
- Produce: `ui.paginas.tablero.render() -> None`, con ruta URL `tablero` y título «Tablero del proyecto».

- [ ] **Paso 1: Crear `ui/paginas/tablero.py`**

```python
"""Pantalla «Tablero del proyecto» (PLAN_SILICE_UI, tarea 4): la vista de un vistazo.

Toma de los tableros de costos de obra lo que el sistema puede respaldar:
* tarjetas de la version vigente (total, costo directo, punto de equilibrio y auditoria);
* anillos y tarjetas del control de obra (avance fisico, SPI, CPI y EAC) cuando hay linea base y
  valuaciones;
* la curva de plan y avance, el desglose del costo por rubro, las partidas de mayor peso y el
  comparativo de versiones.

Solo lectura (RU-10): no abre la version ni escribe. Los datos salen de `ui.tablero` y los graficos
de `ui.graficos`. Texto ajeno solo por `texto_seguro`, en tablas o en tooltips (RU-9).
"""

from __future__ import annotations

from decimal import Decimal

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from seguridad.permisos import Accion
from ui import caso, graficos, tablero
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.estilo import COLOR_ATENCION, COLOR_BIEN, indice, porcentaje
from ui.texto_seguro import texto_seguro

SIN_PROYECTO = (
    "Abra un proyecto con la herramienta Proyecto de la barra superior para ver su tablero."
)
SIN_VERSION = "El proyecto todavia no tiene una version guardada: armela en la Hoja del proyecto."


def render() -> None:
    """El tablero del proyecto abierto, o lo que falta para tenerlo."""
    ui_sesion.exigir(Accion.LEER_PROYECTO)
    proyecto = caso.proyecto_abierto()
    if proyecto is None:
        st.info(SIN_PROYECTO)
        return
    ruta = ruta_caso()
    if not ruta.exists():
        st.info(SIN_PROYECTO)
        return
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            datos = tablero.leer_tablero(sesion, Catalogo(sesion), proyecto)
    except (SQLAlchemyError, ValueError) as error:
        st.error("No se pudo leer el proyecto: " + texto_seguro(str(error)))
        return
    finally:
        motor.dispose()
    if datos is None:
        st.info(SIN_VERSION)
        return
    _encabezado(datos)
    _tarjetas(tablero.tarjetas_del_presupuesto(datos))
    _control(datos)
    _curva_y_desglose(datos)
    _pareto(datos)
    _versiones(datos)


def _encabezado(datos: tablero.DatosTablero) -> None:
    presupuesto = datos.elaboracion.presupuesto
    st.subheader(texto_seguro(datos.proyecto))
    st.caption(
        f"Version vigente {texto_seguro(datos.codigo)} del {datos.fecha.isoformat()} · moneda "
        f"{texto_seguro(presupuesto.moneda)} · {len(presupuesto.partidas)} renglon(es)"
    )


def _tarjetas(tarjetas: list[tablero.Tarjeta]) -> None:
    if not tarjetas:
        return
    for tarjeta, columna in zip(tarjetas, st.columns(len(tarjetas)), strict=True):
        columna.metric(
            tarjeta.rotulo,
            tarjeta.valor,
            help=texto_seguro(tarjeta.detalle) if tarjeta.detalle else None,
            border=True,
        )


def _color_de_indice(valor: Decimal | None) -> str:
    return COLOR_BIEN if valor is not None and valor >= 1 else COLOR_ATENCION


def _control(datos: tablero.DatosTablero) -> None:
    with st.container(border=True):
        st.markdown("**Control de obra**")
        ind = datos.control.indicadores
        if ind is None:
            st.info(texto_seguro(datos.control.motivo))
            return
        avance = tablero.avance_fisico(ind)
        anillos = st.columns(3)
        for columna, rotulo, fraccion, texto, color in (
            (anillos[0], "Avance fisico", avance, porcentaje(avance), None),
            (anillos[1], "SPI (plazo)", ind.spi, indice(ind.spi), _color_de_indice(ind.spi)),
            (anillos[2], "CPI (costo)", ind.cpi, indice(ind.cpi), _color_de_indice(ind.cpi)),
        ):
            with columna:
                st.caption(rotulo)
                opciones = {} if color is None else {"color": color}
                st.altair_chart(
                    graficos.anillo(0.0 if fraccion is None else float(fraccion), texto, **opciones)
                )
        _tarjetas(tablero.tarjetas_de_control(datos.control, datos.elaboracion.presupuesto.moneda))


def _curva_y_desglose(datos: tablero.DatosTablero) -> None:
    presupuesto = datos.elaboracion.presupuesto
    izquierda, derecha = st.columns((3, 2))
    with izquierda, st.container(border=True):
        con_control = datos.control.indicadores is not None
        st.markdown("**Valor ganado (PV, EV, AC)**" if con_control else "**Plan acumulado**")
        filas = tablero.filas_de_curvas(presupuesto, datos.control)
        if filas:
            st.altair_chart(graficos.curvas(filas), width="stretch")
        else:
            st.caption("La version no tiene plan de trabajo: declarelo en la Hoja del proyecto.")
    with derecha, st.container(border=True):
        st.markdown("**Desglose del costo**")
        filas = tablero.filas_de_desglose(presupuesto)
        if not filas:
            st.caption("El total del presupuesto es cero.")
            return
        st.altair_chart(graficos.desglose(filas), width="stretch")
        st.dataframe(
            DataFrame(filas, columns=["Rubro", "Monto", "Peso"]), hide_index=True, width="stretch"
        )


def _pareto(datos: tablero.DatosTablero) -> None:
    filas = tablero.filas_pareto(datos.elaboracion.presupuesto)
    if not filas:
        return
    with st.container(border=True):
        st.markdown("**Partidas de mayor peso** (son las que conviene cotizar primero)")
        grafico, tabla = st.columns((2, 3))
        grafico.altair_chart(graficos.pareto(filas), width="stretch")
        tabla.dataframe(
            DataFrame(filas, columns=["Partida", "Descripcion", "Total", "Peso", "Acumulado"]),
            hide_index=True,
            width="stretch",
        )


def _versiones(datos: tablero.DatosTablero) -> None:
    if not datos.versiones:
        return
    with st.container(border=True):
        st.markdown("**Comparativo de versiones**")
        grafico, tabla = st.columns((2, 3))
        grafico.altair_chart(graficos.versiones(datos.versiones), width="stretch")
        tabla.dataframe(
            DataFrame(
                datos.versiones,
                columns=["Version", "Fecha", "Motivo", "Costo directo", "Total", "Vigente"],
            ),
            hide_index=True,
            width="stretch",
        )
```

Nota: si la versión de Streamlit instalada rechaza `width="stretch"` en `st.altair_chart`, se usa
`use_container_width=True` en esas llamadas. Es la única variante admitida.

- [ ] **Paso 2: Registrar la página en `ui/app.py`**

En el bloque `from ui.paginas import (...)` se agrega `tablero,` en orden alfabético, después de
`simulador,`. En `PAGINAS`, la segunda entrada es la nueva:

```python
PAGINAS: tuple[DefinicionPagina, ...] = (
    PAGINA_INICIO,
    DefinicionPagina(tablero.render, "Tablero del proyecto", SECCION_TRABAJO, accion=_LEE),
    DefinicionPagina(catalogo.render, "Catalogo de partidas e insumos", SECCION_TRABAJO,
                     accion=_LEE),
    # ... el resto sin cambios
)
```

En la docstring de `ui/app.py` se reemplaza «las once pantallas» por «las pantallas» (el número ya
no era exacto).

- [ ] **Paso 3: Revisión del caso sin proyecto ni versión (foco 1)**

Run: `uv run --extra ui --extra api --extra civil python -m streamlit run ui/app.py`
Expected:
- sin proyecto abierto, «Tablero del proyecto» muestra `SIN_PROYECTO`;
- con un proyecto nuevo sin versión, muestra `SIN_VERSION`;
- con el caso de demostración, las tarjetas, la curva del plan, el desglose, el Pareto y el comparativo, y el bloque de control con su motivo.

Un proyecto llamado `Res. *Los* [Pinos]` se ve literal en el subtítulo (foco 5).

- [ ] **Paso 4: Enumeraciones de las pruebas existentes (RU-2, solo con la ratificación de Eugenio)**

`tests/unit/test_ui_importable.py`: en `MODULOS_SIN_PAGINA` agregar `"ui.estilo"`, `"ui.tablero"` y
`"ui.graficos"`; en la aserción, `+ 14` pasa a `+ 15` y el comentario dice «las quince paginas del
marco».

`tests/unit/test_ui_app.py`: en `TITULOS_TRABAJO`, `"Tablero del proyecto"` justo después de
`"Inicio"`.

`tests/unit/test_arquitectura_s5.py`: `"tablero"` en `PAGINAS_QUE_ABREN_EL_CASO`, en orden
alfabético.

Ninguna aserción se borra ni se relaja.

- [ ] **Paso 5: ruff**

Run: `uv run --extra ui ruff check ui/paginas/tablero.py ui/app.py tests/unit/test_ui_importable.py tests/unit/test_ui_app.py tests/unit/test_arquitectura_s5.py && uv run --extra ui ruff format ui/paginas/tablero.py ui/app.py`
Expected: sin hallazgos.

- [ ] **Paso 6: Commit**

```bash
git add ui/paginas/tablero.py ui/app.py tests/unit/test_ui_importable.py tests/unit/test_ui_app.py tests/unit/test_arquitectura_s5.py
git commit -m "feat(ui): pantalla Tablero del proyecto (tarjetas, control, curva, desglose, pareto y versiones)"
```

---

### Tarea 5: Línea de estado en la barra superior

**Files:**
- Modify: `ui/caso.py` (al final)
- Modify: `ui/barra.py` (función nueva `pintar_estado`)
- Modify: `ui/app.py` (`marco()`)
- Modify: `ui/paginas/hoja.py` (`render()`)

**Interfaces:**
- Produce:
  - `ui.caso.ResumenDeTrabajo(proyecto: str, version: str | None, estado: str, total: str)`
  - `ui.caso.publicar_resumen(resumen: ResumenDeTrabajo | None) -> None`
  - `ui.caso.resumen_publicado() -> ResumenDeTrabajo | None`
  - `ui.barra.pintar_estado() -> None`

La maqueta pide «Proyecto · Estado · Total» arriba. La barra no conoce las claves de la hoja (SF4),
así que la hoja **publica** un resumen en `ui.caso` y la barra lo lee. Para que no muestre el resumen
de la ejecución anterior, `marco()` reserva un hueco bajo la barra y lo llena **después** de pintar
la pantalla.

- [ ] **Paso 1: `ui/caso.py`, al final del módulo**

```python
# --- resumen de trabajo para la barra (PLAN_SILICE_UI, tarea 5) ------------------------------------

CLAVE_RESUMEN = "caso_resumen_de_trabajo"  # clave propia, no de widget


@dataclass(frozen=True, slots=True)
class ResumenDeTrabajo:
    """Lo que la hoja publica para la linea de estado de la barra: textos ya formateados.

    `proyecto` y `version` son texto ajeno: quien los pinte los escapa (RU-9).
    """

    proyecto: str
    version: str | None
    estado: str
    total: str


def publicar_resumen(resumen: ResumenDeTrabajo | None) -> None:
    """La hoja deja su resumen (o lo retira con `None`)."""
    if resumen is None:
        st.session_state.pop(CLAVE_RESUMEN, None)
    else:
        st.session_state[CLAVE_RESUMEN] = resumen


def resumen_publicado() -> ResumenDeTrabajo | None:
    resumen = st.session_state.get(CLAVE_RESUMEN)
    return resumen if isinstance(resumen, ResumenDeTrabajo) else None
```

Si `ui/caso.py` no importa `dataclass`, se agrega `from dataclasses import dataclass` (ya lo usa
`EstadoCaso`).

- [ ] **Paso 2: `ui/barra.py`, función nueva después de `pintar_barra`**

Se agrega `resumen_publicado` al `from ui.caso import (...)` y
`from ui.texto_seguro import texto_seguro` a los imports.

```python
def pintar_estado() -> None:
    """La linea de estado bajo la barra: proyecto, version, estado y total (PLAN_SILICE_UI, 5).

    El total y el estado solo aparecen si la hoja publico el resumen del proyecto abierto; si no,
    la version vigente guardada. Todo texto ajeno pasa por `texto_seguro` (RU-9).
    """
    abierto = proyecto_abierto()
    if abierto is None:
        return
    resumen = resumen_publicado()
    if resumen is not None and resumen.proyecto == abierto:
        partes = [f"Proyecto: {texto_seguro(abierto)}"]
        if resumen.version is not None:
            partes.append(f"Version {texto_seguro(resumen.version)}")
        partes += [f"Estado: {resumen.estado}", f"Total: {texto_seguro(resumen.total)}"]
    else:
        vigente = version_vigente(ruta_caso(), abierto)
        partes = [f"Proyecto: {texto_seguro(abierto)}"]
        partes.append(
            "sin version guardada"
            if vigente is None
            else f"Version vigente {texto_seguro(vigente.codigo)} del {vigente.fecha.isoformat()}"
        )
    st.caption(" · ".join(partes))
```

- [ ] **Paso 3: `ui/app.py`, en `marco()`**

Inmediatamente después de la llamada a `barra.pintar_barra(...)`, dentro del mismo `if`:

```python
        estado = st.empty()  # se llena al final: ve el resumen que la pantalla publica ahora
```

Y después de `pintar()`, antes del botón «Siguiente»:

```python
    if puede_editar:
        with estado.container():
            barra.pintar_estado()
```

`puede_editar` es la condición que ya decide si se pinta la barra. Si hoy está escrita en línea, se
guarda en una variable con ese nombre, sin cambiar la condición.

- [ ] **Paso 4: `ui/paginas/hoja.py`, al final de `render()`**

Se agrega `from ui.estilo import dinero` (o se reutiliza `_dinero`) y, después del bloque
`with panel: ...`:

```python
    _publicar_resumen()
```

Y la función, junto a `_mostrar_mensaje`:

```python
def _publicar_resumen() -> None:
    """Lo que la barra muestra en su linea de estado (PLAN_SILICE_UI, tarea 5)."""
    abierta = _abierta()
    proyecto = abierta.proyecto if abierta is not None else caso.proyecto_abierto()
    if proyecto is None:
        caso.publicar_resumen(None)
        return
    resultado, cambios = _calculo()
    presupuesto = resultado.elaboracion.presupuesto
    if cambios:
        estado = f"borrador con {len(cambios)} cambio(s) sin guardar"
    elif abierta is not None:
        estado = "guardada"
    else:
        estado = "borrador nuevo"
    caso.publicar_resumen(
        caso.ResumenDeTrabajo(
            proyecto=proyecto,
            version=None if abierta is None else abierta.codigo,
            estado=estado,
            total=_dinero(presupuesto.total, presupuesto.moneda),
        )
    )
```

- [ ] **Paso 5: ruff y revisión en el navegador**

Run: `uv run --extra ui ruff check ui/caso.py ui/barra.py ui/app.py ui/paginas/hoja.py && uv run --extra ui ruff format ui/caso.py ui/barra.py ui/app.py ui/paginas/hoja.py`
Expected: sin hallazgos.

En el navegador:
- con un proyecto abierto y una versión en la hoja, la línea dice «Proyecto: … · Version … · Estado: guardada · Total: …»;
- al editar una cantidad, en la **misma** ejecución pasa a «borrador con 1 cambio(s) sin guardar» con el total nuevo;
- en otra pantalla, se ve el último resumen de la hoja de ese proyecto;
- con otro proyecto, se ve su versión vigente.

- [ ] **Paso 6: Commit**

```bash
git add ui/caso.py ui/barra.py ui/app.py ui/paginas/hoja.py
git commit -m "feat(ui): linea de estado bajo la barra con proyecto, version, estado y total"
```

---

### Tarea 6: Pestaña APU en tres paneles

**Files:**
- Modify: `ui/hoja.py` (dos funciones puras nuevas, junto a `filas_de_apu`)
- Modify: `ui/paginas/hoja.py` (`_pestana_apu`, `_formulario_de_insumo`, `_calculado_de_apu`, `_pestana_parametros`; ayudantes nuevos)

**Interfaces:**
- Consume: `ui.estilo.porcentaje` (tarea 1); `hoja.parametros_desde_texto`, `hoja.CAMPOS_PARAMETROS`, `hoja.insumos_candidatos`, `hoja.texto_numero`; `core.verification.texto.normalizar_texto`.
- Produce:
  - `ui.hoja.filtrar_partidas(codigos: Sequence[str], descripciones: Mapping[str, str], texto: str) -> list[str]`
  - `ui.hoja.filas_de_cierre(r: ResultadoAPU, parametros: ParametrosCosto, moneda: str) -> list[dict[str, str]]`

- [ ] **Paso 1: Las dos funciones puras en `ui/hoja.py`**

`ResultadoAPU` se importa de `core.contracts.apu` si aún no está, `normalizar_texto` de
`core.verification.texto` y `porcentaje` de `ui.estilo` (sin Streamlit: la regla de `ui/hoja.py` se
cumple).

```python
def filtrar_partidas(
    codigos: Sequence[str], descripciones: Mapping[str, str], texto: str
) -> list[str]:
    """Los codigos cuyo codigo o descripcion contienen `texto`, sin acentos ni mayusculas
    (PLAN_SILICE_UI, tarea 6). Sin texto, todos; el orden de `codigos` se conserva."""
    buscado = normalizar_texto(texto).strip()
    if not buscado:
        return list(codigos)
    return [
        c
        for c in codigos
        if buscado in normalizar_texto(c) or buscado in normalizar_texto(descripciones.get(c, ""))
    ]


def filas_de_cierre(
    r: ResultadoAPU, parametros: ParametrosCosto, moneda: str
) -> list[dict[str, str]]:
    """El cierre de una partida, del costo directo al precio unitario, con la misma cascada de
    `core.costing.motor.calcular_apu` (montos por unidad de partida)."""

    def monto(valor: Decimal) -> str:
        return f"{formatear_decimal(valor, DECIMALES_PRESENTACION)} {moneda}"

    return [
        {"Concepto": "Materiales", "Monto": monto(r.materiales), "Nota": "completos"},
        {"Concepto": "Equipos", "Monto": monto(r.equipos), "Nota": "entre el rendimiento"},
        {
            "Concepto": "Mano de obra",
            "Monto": monto(r.mano_obra),
            "Nota": (
                f"FCAS {texto_numero(parametros.fcas)} y bono "
                f"{texto_numero(parametros.bono_alimentacion)}, entre el rendimiento"
            ),
        },
        {"Concepto": "= Costo directo", "Monto": monto(r.costo_directo), "Nota": ""},
        {
            "Concepto": "+ Administracion",
            "Monto": monto(r.con_administracion - r.costo_directo),
            "Nota": f"{porcentaje(parametros.administracion)} del costo directo",
        },
        {"Concepto": "= Con administracion", "Monto": monto(r.con_administracion), "Nota": ""},
        {
            "Concepto": "+ Utilidad",
            "Monto": monto(r.precio_unitario - r.con_administracion),
            "Nota": f"{porcentaje(parametros.utilidad)} en cascada",
        },
        {"Concepto": "= Precio unitario", "Monto": monto(r.precio_unitario), "Nota": ""},
    ]
```

Si `DECIMALES_PRESENTACION` no está importado en `ui/hoja.py`, se importa de
`core.verification.informe`.

- [ ] **Paso 2: Lista de partidas (panel izquierdo) en `ui/paginas/hoja.py`**

Junto a `_codigos_valorados`:

```python
CLAVE_PARTIDA_APU = "hoja_apu_partida"
CLAVE_FILTRO_APU = "hoja_apu_filtro"
ANCHOS_APU = (1.1, 3.2, 1.6)  # partidas · tabla del APU · cierre de partida


def _lista_de_partidas(resultado: hoja.ResultadoHoja, codigos: list[str]) -> str:
    """Panel izquierdo: buscador y lista de las partidas valoradas (RU-6: no hay capitulos)."""
    descripciones = {
        p.item.codigo_partida: p.apu.descripcion for p in resultado.elaboracion.presupuesto.partidas
    }
    st.markdown("**Partidas**")
    texto = st.text_input(
        "Buscar partida", key=CLAVE_FILTRO_APU, placeholder="codigo o descripcion"
    )
    visibles = hoja.filtrar_partidas(codigos, descripciones, texto)
    if not visibles:
        st.caption("Ninguna partida coincide; se muestran todas.")
        visibles = codigos
    if st.session_state.get(CLAVE_PARTIDA_APU) not in visibles:
        st.session_state.pop(CLAVE_PARTIDA_APU, None)  # foco 4: nunca un valor fuera de la lista
    return st.radio(
        "Partida",
        visibles,
        format_func=lambda c: texto_seguro(f"{c} · {descripciones.get(c, '')}"),
        key=CLAVE_PARTIDA_APU,
        label_visibility="collapsed",
    )
```

Se agrega `from ui.texto_seguro import texto_seguro` a los imports.

- [ ] **Paso 3: Tabla del APU por rubro (panel central)**

Se reemplaza el cuerpo de `_pestana_apu` por los tres paneles, y el código que hoy pinta las tablas
pasa a `_tabla_de_apu`. Las claves de los editores (`_clave("apu", codigo, rotulo)` y
`_clave("rendimiento", codigo)`) **no cambian**.

```python
def _pestana_apu() -> None:
    resultado, _ = _calculo()
    codigos = _codigos_valorados(resultado)
    if not codigos:
        st.info("Todavia no hay partidas valoradas: derive cantidades en Espacio y metrajes.")
        return
    izquierda, centro, derecha = st.columns(ANCHOS_APU, gap="medium")
    with izquierda:
        codigo = _lista_de_partidas(resultado, codigos)
    with centro:
        _tabla_de_apu(codigo)
    with derecha:
        _cierre_de_partida(codigo)


def _subtotal_de_rubro(codigo: str, clave: str) -> str:
    resultado, _ = _calculo()
    renglon = _renglon(resultado, codigo)
    if renglon is None:
        return ""
    valor = {"materiales": renglon.resultado.materiales, "equipos": renglon.resultado.equipos,
             "mano de obra": renglon.resultado.mano_obra}[clave]
    return _dinero(valor, resultado.elaboracion.presupuesto.moneda)


def _renglon(resultado: hoja.ResultadoHoja, codigo: str) -> Any:
    return next(
        (p for p in resultado.elaboracion.presupuesto.partidas if p.item.codigo_partida == codigo),
        None,
    )


def _tabla_de_apu(codigo: str) -> None:
    """Panel central: un bloque por rubro con su subtotal, el rendimiento y el cambio de insumo.
    Cada edicion recalcula en el servidor (RU-5)."""
    borrador, siembra = _borrador(), _partida()
    actual = borrador.composiciones[codigo]
    inicial = siembra.composiciones.get(codigo, actual)
    st.caption(
        f"{texto_seguro(actual.descripcion)} · unidad {texto_seguro(actual.unidad)}. Se edita la "
        "cantidad de cada linea y el rendimiento, en la copia de esta version: el catalogo no "
        "cambia."
    )
    tablas = hoja.filas_de_apu(inicial)
    editadas = []
    for (clave, rotulo, columnas), filas in zip(_GRUPOS_APU, tablas, strict=True):
        with st.expander(
            f"{rotulo} · {len(filas)} linea(s) · {_subtotal_de_rubro(codigo, clave)}",
            expanded=True,
        ):
            if not filas:
                st.caption("Sin lineas.")
                editadas.append([])
                continue
            tabla = st.data_editor(
                DataFrame(filas, columns=list(columnas), dtype=str),
                hide_index=True,
                width="stretch",
                disabled=[c for c in columnas if c != "cantidad"],
                key=_clave("apu", codigo, rotulo),
            )
            editadas.append(tabla.to_dict("records"))
    rendimiento = st.text_input(
        "Rendimiento (unidades por dia)",
        value=hoja.texto_numero(inicial.rendimiento),
        key=_clave("rendimiento", codigo),
    )
    try:
        nueva = hoja.composicion_con_cantidades(actual, *editadas, rendimiento)
        if nueva != actual:
            _poner_borrador(
                replace(borrador, composiciones={**borrador.composiciones, codigo: nueva})
            )
    except hoja.HojaInvalida as error:
        st.error(f"{texto_seguro(str(error))}. La hoja sigue con el ultimo APU valido.")
    _formulario_de_insumo(codigo, _borrador().composiciones[codigo])
```

Si `hoja.composicion_con_cantidades` lee las celdas, ya lo hace con `texto_de_celda`; aquí no se lee
ninguna celda a mano. El rótulo del expander lleva un subtotal que puede quedar una ejecución
atrasado respecto de la edición en curso. El cierre de la derecha, que se pinta después, siempre
está al día.

- [ ] **Paso 4: Selector de insumo con autocompletado**

En `_formulario_de_insumo` se reemplazan el `st.text_input("Buscar insumo por nombre", ...)` y la
consulta que filtraba por texto por un solo `st.selectbox`, que filtra al escribir:

```python
LIMITE_INSUMOS = 300  # el selectbox filtra en el navegador; mas alla, se acota en la base
```

```python
        acotar = ""
        with _sesion() as sesion:
            candidatos = (
                []
                if sesion is None
                else hoja.insumos_candidatos(
                    sesion, abierta.proyecto, abierta.codigo, tipo, acotar, limite=LIMITE_INSUMOS
                )
            )
        if len(candidatos) == LIMITE_INSUMOS:
            acotar = st.text_input(
                f"Hay mas de {LIMITE_INSUMOS} insumos: escriba parte del nombre para acotar",
                key=_clave("buscar", codigo),
            )
            if acotar.strip():
                with _sesion() as sesion:
                    candidatos = hoja.insumos_candidatos(
                        sesion, abierta.proyecto, abierta.codigo, tipo, acotar,
                        limite=LIMITE_INSUMOS,
                    )
        if not candidatos:
            st.caption("Ningun insumo de la lista coincide: pruebe con otra palabra.")
            return
        elegido = st.selectbox(
            "Insumo (escriba para buscar por codigo o descripcion)",
            candidatos,
            index=None,
            placeholder="Elegir insumo de la lista de precios",
            format_func=lambda c: f"{c.codigo} · {c.descripcion} · {c.unidad} · {c.precio:f}",
            key=_clave("insumo", codigo),
        )
        st.button(
            "Usar este insumo",
            on_click=_cambiar_insumo,
            args=(codigo, tipo, indice, elegido),
            key=_clave("usar", codigo),
            disabled=elegido is None,
        )
```

Las opciones de `st.selectbox` son texto plano, no Markdown.

- [ ] **Paso 5: Cierre de partida con los factores (panel derecho) y parámetros compartidos**

Se extrae la edición de parámetros de `_pestana_parametros` a un ayudante que usan las dos
pantallas (RU-7). Cada una lleva su propio prefijo de clave:

```python
def _editar_parametros(contenedores: Sequence[Any], prefijo: str) -> None:
    """Un campo exacto por parametro de costo (RU-7); un cambio valido recalcula todos los APU."""
    borrador, siembra = _borrador(), _partida()
    textos = {}
    for campo, contenedor in zip(hoja.CAMPOS_PARAMETROS, contenedores, strict=True):
        textos[campo] = contenedor.text_input(
            _ROTULOS_PARAMETROS[campo],
            value=str(getattr(siembra.parametros, campo)),
            key=_clave(prefijo, campo),
        )
    try:
        parametros = hoja.parametros_desde_texto(textos)
        if parametros != borrador.parametros:
            _poner_borrador(replace(borrador, parametros=parametros))
    except hoja.HojaInvalida as error:
        st.error(f"{texto_seguro(str(error))}. La hoja sigue con los ultimos parametros validos.")
```

`_pestana_parametros` queda:

```python
def _pestana_parametros() -> None:
    st.caption(
        "Los parametros de costo de esta version. Cambiarlos recalcula todos sus APU; el cambio "
        "queda en el registro con su fuente."
    )
    _editar_parametros(st.columns(len(hoja.CAMPOS_PARAMETROS)), "param")
    resultado, cambios = _calculo()
    presupuesto = resultado.elaboracion.presupuesto
    st.metric("Total del presupuesto", _dinero(presupuesto.total, presupuesto.moneda))
    _moneda(cambios)
```

El panel derecho:

```python
def _cierre_de_partida(codigo: str) -> None:
    """Panel derecho: factores de la version y el cierre paso a paso de la partida elegida.
    Imprevistos no existe en el modelo (RU-3)."""
    with st.container(border=True):
        st.markdown("**Factores de la version**")
        _editar_parametros([st] * len(hoja.CAMPOS_PARAMETROS), "factor")
    resultado, _ = _calculo()
    renglon = _renglon(resultado, codigo)
    if renglon is None:
        return
    with st.container(border=True):
        st.markdown("**Cierre de partida**")
        st.dataframe(
            DataFrame(
                hoja.filas_de_cierre(
                    renglon.resultado, _borrador().parametros, resultado.elaboracion.presupuesto.moneda
                ),
                columns=["Concepto", "Monto", "Nota"],
            ),
            hide_index=True,
            width="stretch",
        )
        _calculado_de_apu(resultado, codigo)
```

`_calculado_de_apu` deja de usar `st.columns(4)`, porque el panel es angosto, y pinta las cuatro
métricas una debajo de otra con los **mismos rótulos** («Materiales», «Equipos», «Mano de obra» y
«Precio unitario»; `test_ui_hoja.py:229`). Usa `_renglon`:

```python
def _calculado_de_apu(resultado: hoja.ResultadoHoja, codigo: str) -> None:
    renglon = _renglon(resultado, codigo)
    if renglon is None:
        return
    moneda = resultado.elaboracion.presupuesto.moneda
    r = renglon.resultado
    st.metric("Materiales", _dinero(r.materiales, moneda))
    st.metric("Equipos", _dinero(r.equipos, moneda))
    st.metric("Mano de obra", _dinero(r.mano_obra, moneda))
    st.metric("Precio unitario", _dinero(r.precio_unitario, moneda), border=True)
    for fila in hoja.filas_del_presupuesto(resultado):
        if fila["partida"] == codigo and fila["estado"] != hoja.TEXTO_OK:
            st.caption(texto_seguro(f"Estado de {fila['clave']}: {fila['estado']}"))
```

Las claves `_clave("factor", campo)` y `_clave("param", campo)` son de pestañas distintas y solo una
se ejecuta a la vez. Al cambiar de pestaña, `_resembrar` renueva la siembra, así que las dos parten
de los parámetros vigentes.

- [ ] **Paso 6: ruff**

Run: `uv run --extra ui ruff check ui/hoja.py ui/paginas/hoja.py && uv run --extra ui ruff format ui/hoja.py ui/paginas/hoja.py`
Expected: sin hallazgos.

- [ ] **Paso 7: Revisión en el navegador** (focos 4 y 5)

Hoja del proyecto → pestaña APU, con el caso de demostración:
- se ven tres paneles; a la izquierda, la lista con buscador; al buscar «tub» o «TUB» quedan las mismas partidas; con un texto sin coincidencias, la lista vuelve a todas y no aparece error;
- al centro, tres bloques (Materiales, Equipos y Mano de obra) con su número de líneas y su subtotal; al cambiar una cantidad, el cierre de la derecha y el «Precio unitario» cambian en la misma ejecución, y la línea de estado de la barra dice «borrador con 1 cambio(s)»;
- con `administracion` en `0.12`, el cierre muestra «12.0 % del costo directo» y el precio unitario se recalcula; con `abc`, aparece el error y la hoja sigue con el último valor válido;
- el selector de insumo filtra al escribir, «Usar este insumo» queda deshabilitado hasta elegir uno, y al usarlo cambia la línea y el cierre;
- la pestaña Parámetros sigue funcionando y muestra los mismos valores que el panel derecho;
- una descripción de partida con `*` o `_` se ve literal en la lista.

- [ ] **Paso 8: Commit**

```bash
git add ui/hoja.py ui/paginas/hoja.py
git commit -m "feat(ui): pestana APU en tres paneles con lista de partidas, rubros y cierre de partida"
```

---

### Tarea 7: Documentos, bitácora, revisión de Eugenio y PR **[HUMANO]**

**Files:**
- Modify: `NORMAS.md` §6 (líneas de `ui/`)
- Modify: `docs/manual_usuario.md` (secciones nuevas)
- Modify: `CHANGELOG.md` (sección sin publicar)
- Create: `docs/bitacora/2026-10-12-interfaz-de-trabajo.md`

- [ ] **Paso 1: `NORMAS.md` §6**

En la lista de módulos de `ui/`, se agrega:

```markdown
- `estilo.py` (paleta y formatos), `tablero.py` (datos del tablero, solo lectura) y `graficos.py`
  (graficos en Altair): sin Streamlit (PLAN_SILICE_UI).
- `paginas/tablero.py` («Tablero del proyecto»).
```

- [ ] **Paso 2: `docs/manual_usuario.md`**

Dos secciones nuevas:

```markdown
## Tablero del proyecto

Muestra de un vistazo la version vigente del proyecto abierto. Las cuatro tarjetas son el total
del contrato, el costo directo, el punto de equilibrio y el resultado de la auditoria. Si el
proyecto tiene linea base y valuaciones, se agregan los anillos de avance fisico, SPI y CPI, el
costo final estimado y la curva PV, EV y AC; si no, el tablero dice que falta. Debajo estan el
desglose del costo por rubro, las partidas de mayor peso (las primeras que conviene cotizar) y el
comparativo de versiones. Solo lee: para cambiar algo, use la Hoja del proyecto.

## APU en tres paneles

En la pestana APU de la hoja, la columna izquierda lista las partidas valoradas y tiene un
buscador por codigo o descripcion. La del centro muestra el APU de la partida elegida por rubro
(materiales, equipos y mano de obra), cada uno con su subtotal; se editan la cantidad de cada
linea y el rendimiento, y el insumo de una linea se cambia con un selector que busca al escribir.
La de la derecha tiene los factores de la version (FCAS, bono, administracion y utilidad) y el
cierre de la partida, del costo directo al precio unitario. Cada cambio recalcula al momento y la
barra superior indica cuantos cambios faltan por guardar.
```

- [ ] **Paso 3: `CHANGELOG.md`, en la sección sin publicar**

```markdown
### Interfaz de trabajo (PLAN_SILICE_UI)
- Pantalla «Tablero del proyecto»: tarjetas, control de obra (avance, SPI, CPI y EAC), curva,
  desglose del costo, partidas de mayor peso y comparativo de versiones.
- Linea de estado bajo la barra superior: proyecto, version, estado y total.
- Pestana APU en tres paneles: lista de partidas, APU por rubro y cierre de partida con factores.
- Tema visual en `.streamlit/config.toml`; Altair declarado en el extra `ui`.
```

- [ ] **Paso 4: Bitácora `docs/bitacora/2026-10-12-interfaz-de-trabajo.md`**

```markdown
# Interfaz de trabajo de Silice 1.0.0 (PLAN_SILICE_UI)

**Fecha:** 2026-10-12 · **Rama:** `inc/silice-ui`

## Que se hizo
Tema visual; tablero del proyecto; linea de estado en la barra; pestana APU en tres paneles. Sin
cambios en core/, adapters/, api/ ni en la base.

## Sin prueba (RU-1, para la auditoria final)
- `ui/estilo.py`, `ui/tablero.py` (desglose que suma el total, pareto con resto, curvas con y sin
  control, control no disponible), `ui/graficos.py`.
- `ui/paginas/tablero.py` (sin proyecto, sin version, con control, texto ajeno).
- `ui.caso.publicar_resumen` / `ui.barra.pintar_estado` (resumen del mismo ciclo).
- `ui.hoja.filtrar_partidas`, `ui.hoja.filas_de_cierre` (cascada igual a `calcular_apu`) y la
  pestana APU (filtro vacio, factor invalido, selector de insumo).

## Rulings
RU-1 a RU-12 del plan. RU-2 (enumeraciones de pruebas existentes) ratificado por Eugenio el
<fecha de la ratificacion>.

## Hallazgo fuera de alcance
`ui/barra.py` interpola el nombre del proyecto sin `texto_seguro` en dos `st.markdown` (§0.4 del
plan); `ui/resultado.py::_pendientes` igual con descripciones.
```

La fecha de la ratificación se escribe cuando Eugenio ratifique RU-2. Si no la ratifica, la línea dice
«RU-2 no ratificado: el tablero no se registró en el menú» y el paso 2 de la tarea 4 se revierte.

- [ ] **Paso 5: ruff global de lo tocado y empuje**

Run:
```bash
uv run --extra ui ruff check ui tests/unit/test_ui_importable.py tests/unit/test_ui_app.py tests/unit/test_arquitectura_s5.py
git add NORMAS.md docs/manual_usuario.md CHANGELOG.md docs/bitacora/2026-10-12-interfaz-de-trabajo.md
git commit -m "docs: interfaz de trabajo en NORMAS, manual, changelog y bitacora"
git push -u origin inc/silice-ui
```

- [ ] **Paso 6: PR y CI**

```bash
gh pr create --base main --title "Interfaz de trabajo: tablero, linea de estado y APU en tres paneles" --body-file -
```

El cuerpo resume las tareas 1 a 6, los rulings RU-1 a RU-12 y lo que queda sin prueba, y termina
con la línea de atribución del sistema. Si la CI se pone roja por una prueba existente, se corrige el
código; la prueba solo se toca si es una de las tres enumeraciones de RU-2.

- [ ] **Paso 7: [HUMANO] Revisión de Eugenio en el navegador**

El agente se detiene aquí y lo dice. Eugenio recorre el Tablero, la línea de estado y la pestaña APU
con su caso y aprueba, o deja observaciones en el PR. La fusión espera su visto bueno.
