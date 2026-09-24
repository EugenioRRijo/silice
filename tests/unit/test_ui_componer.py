"""Primeras pruebas de interfaz del repositorio (Sesión P4.1): la pantalla de componer.

Hasta esta sesión, `ui/paginas/componer.py` (UC‑10 y UC‑11) solo tenía la prueba de humo de
`tests/unit/test_ui_importable.py` (se importa sin efectos) y la prueba de extremo a extremo que
recorre `ui.composicion.composicion_desde_tablas` sin Streamlit
(`tests/integration/test_composicion_extremo_a_extremo.py`). Esta es la primera vez que el
repositorio ejercita la pantalla misma con `streamlit.testing.v1.AppTest` (Streamlit 1.62.0).

**Caso de prueba, no ejecución real** (CLAUDE.md §1): las composiciones que se guardan aquí son
`APU_TUBERIA` de la línea base (`tests/fixtures/apu_linea_base.py`), reetiquetada con el código
propio `UI-01-TUB` para no depender de si la base sembrada ya trae las partidas `LB-*`; las
"condiciones del rendimiento" que se teclean son texto de prueba, no una observación de obra.

Qué puede y qué no puede hacer `AppTest` con esta pantalla (comprobado con dos experimentos
desechables contra `f884044`, no supuesto):

1. `st.data_editor` no se puede teclear desde `AppTest`: las tres tablas de insumos y la de
   cantidades de obra se siembran por `st.session_state[f"{clave}__filas"]` **antes** del primer
   `at.run()` (la página solo inicializa esa clave si no existe; sembrar después de que la tabla ya
   se pintó no surte efecto).
2. La base se desvía sin tocar código de producción, parchando el **objeto módulo** que devuelve
   `importlib.import_module("ui.caso")`, donde vive la única `RUTA_BASE_POR_DEFECTO` desde el
   sprint de UI (el que vive en `sys.modules`, que es el que ejecuta `AppTest`), no una ruta de
   texto: `monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))` antes del primer
   `run()`. La forma de texto
   (`monkeypatch.setattr("ui.paginas.componer.RUTA_BASE_POR_DEFECTO", ...)`) se abandonó adrede:
   `tests/unit/test_composicion_ia.py::_SinExtraML` deja el atributo `componer` del paquete
   `ui.paginas` apuntando a una copia fría que `sys.modules` ya no usa (diagnosticado en la Tarea
   1; el arreglo de raíz vive en ese archivo). `monkeypatch.setattr` con una ruta de texto resuelve
   por ese atributo de paquete (`getattr`) y aterriza en la copia huérfana sin ningún efecto;
   parchar el objeto de `sys.modules` directamente no depende de ese atributo.
3. La ayuda 1 (`sugerir_partidas_similares`) carga `sentence-transformers` en cuanto el catálogo no
   está vacío y hay una descripción tecleada: se sustituye por un doble que no sugiere nada.
4. Los widgets se localizan por su rótulo (`_por_rotulo`), salvo las condiciones del rendimiento,
   que son el único `st.text_area` de la página y se localizan por posición (`at.text_area[0]`).

Ninguna prueba de este archivo toca `data/apu.db`: todas usan `tmp_path` y abren su propio motor
SQLAlchemy para verificar lo que la pantalla guardó, cerrándolo siempre con `motor.dispose()`
(Windows no permite borrar un archivo con un motor todavía abierto).
"""

from __future__ import annotations

import dataclasses
import importlib
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ElementList

from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.costing import calcular_apu
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from scripts.seed_demo import main as seed_demo_main
from tests.fixtures.apu_linea_base import (
    APU_TUBERIA,
    PARAMETROS_LINEA_BASE,
    PRECIO_UNITARIO_ESPERADO,
)
from tests.integration.test_composicion_extremo_a_extremo import (
    _filas_equipos,
    _filas_mano_obra,
    _filas_materiales,
    _texto,
)
from ui.paginas import componer

SCRIPT = "from ui.paginas.componer import render\nrender()\n"

#: `APU_TUBERIA` de la línea base, con un código propio (ver docstring del módulo): así ninguna de
#: estas pruebas depende de si la base sembrada ya trae las partidas `LB-*`.
CODIGO_UI = "UI-01-TUB"
APU_UI = dataclasses.replace(APU_TUBERIA, codigo_partida=CODIGO_UI)

#: Condiciones de prueba para RF-33: cualquier texto no vacío basta; declara explícitamente que es
#: de prueba, no una observación de obra (CLAUDE.md §1).
CONDICIONES_DE_PRUEBA = (
    "condiciones de prueba de la Sesión P4.1 (tests/unit/test_ui_componer.py): no proviene de una "
    "ejecución medida"
)

#: Misma tolerancia que `tests/integration/test_composicion_extremo_a_extremo.py`: se deriva de la
#: precisión de presentación del núcleo en vez de teclear "0.01".
TOLERANCIA_PU = Decimal(1).scaleb(-DECIMALES_PRESENTACION)


def _pantalla(monkeypatch, base: Path, filas: dict[str, list[dict[str, str]]]) -> AppTest:
    """La pantalla contra `base`, con las tablas precargadas y la ayuda 1 sustituida por un doble.

    Parcha el **objeto módulo** de `sys.modules["ui.paginas.componer"]` (el que `importlib.
    import_module` devuelve, el mismo que ejecuta `AppTest` al resolver `from ui.paginas.componer
    import render`), no una ruta de texto: ver el hecho verificado 2, arriba, y el informe de la
    Tarea 1 para el porqué (`tests/unit/test_composicion_ia.py::_SinExtraML` deja el atributo del
    paquete desincronizado de `sys.modules`, y una ruta de texto resuelve por ese atributo).
    """
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.componer")
    monkeypatch.setattr(pagina, "sugerir_partidas_similares", lambda *_: [])
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    for clave, valor in filas.items():
        at.session_state[clave] = valor
    at.run()
    assert base.exists(), (
        f"la redireccion de ui.caso.RUTA_BASE_POR_DEFECTO no surtio efecto: {base} no existe "
        "tras el primer run (la pantalla habria creado el esquema ahi)"
    )
    assert not at.exception, f"la pantalla no debia fallar al abrir: {at.exception}"
    return at


def _filas_de_apu(apu) -> dict[str, list[dict[str, str]]]:
    """Las tres tablas de insumos de `apu`, listas para sembrar `st.session_state`."""
    return {
        "componer_materiales__filas": _filas_materiales(apu),
        "componer_equipos__filas": _filas_equipos(apu),
        "componer_mano_obra__filas": _filas_mano_obra(apu),
    }


def _por_rotulo(elementos: ElementList, rotulo: str):
    """El primer elemento de `elementos` (widgets, métricas, botones…) con ese rótulo exacto."""
    for elemento in elementos:
        if elemento.label == rotulo:
            return elemento
    raise AssertionError(
        f"ningun elemento con el rotulo {rotulo!r}; rotulos disponibles: "
        f"{[elemento.label for elemento in elementos]}"
    )


def _teclear_cabecera(at: AppTest, apu, *, con_rendimiento: bool = True) -> None:
    """Teclea código, descripción y unidad de `apu`, localizando cada campo por su rótulo.

    El rendimiento (`_texto(apu.rendimiento)`) se teclea salvo que `con_rendimiento` sea falso: la
    prueba 3 necesita dejarlo en blanco a propósito (mitad de RF-33 que la prueba 2 no cubre).
    """
    _por_rotulo(at.text_input, "Codigo").set_value(apu.codigo_partida)
    _por_rotulo(at.text_input, "Descripcion").set_value(apu.descripcion)
    _por_rotulo(at.text_input, "Unidad").set_value(apu.unidad)
    if con_rendimiento:
        _por_rotulo(at.text_input, componer.RENDIMIENTO_ETIQUETA).set_value(_texto(apu.rendimiento))


@contextmanager
def _catalogo_en(base: Path) -> Iterator[Catalogo]:
    """Un `Catalogo` nuevo contra `base`, para verificar lo que la pantalla guardó.

    Motor propio, distinto del que abre `render()` en cada `at.run()`: se cierra siempre con
    `motor.dispose()` (regla global del plan; en Windows un motor abierto impide borrar el
    temporal).
    """
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield Catalogo(sesion)
    finally:
        motor.dispose()


def _sembrar_base(base: Path) -> None:
    """Siembra el caso de demostración en `base` (script real, sobre un archivo temporal)."""
    assert seed_demo_main(["--db", str(base)]) == 0


# -------------------------------------------------------------------------------------------
# 1. El desglose en vivo (UC-10, paso 6): no hace falta guardar para ver el precio unitario
# -------------------------------------------------------------------------------------------


def test_el_desglose_en_vivo_muestra_el_precio_unitario(monkeypatch, tmp_path):
    """Base vacía, tablas sembradas y cabecera tecleada: el precio unitario se ve sin guardar."""
    base = tmp_path / "vacia.db"

    at = _pantalla(monkeypatch, base, _filas_de_apu(APU_UI))
    _teclear_cabecera(at, APU_UI)
    at.run()

    assert not at.exception

    resultado = calcular_apu(APU_UI, PARAMETROS_LINEA_BASE)
    metrica = _por_rotulo(at.metric, "Precio unitario")

    # INV-045: la pantalla presenta con la fuente unica (dos decimales), no `str(Decimal)`.
    assert metrica.value == formatear_decimal(resultado.precio_unitario, DECIMALES_PRESENTACION)
    assert abs(resultado.precio_unitario - PRECIO_UNITARIO_ESPERADO["LB-02-TUB"]) <= TOLERANCIA_PU


def test_el_desglose_en_vivo_presenta_dos_decimales(monkeypatch, tmp_path):
    """INV-045. Oraculo: CLAUDE.md §4 (tuberia: costo directo 8,058; PU 10,19) y la fixture."""
    at = _pantalla(monkeypatch, tmp_path / "vacia.db", _filas_de_apu(APU_UI))
    _teclear_cabecera(at, APU_UI)
    at.run()
    assert not at.exception

    assert _por_rotulo(at.metric, "Costo directo").value == "8.06"
    assert _por_rotulo(at.metric, "Precio unitario").value == str(
        PRECIO_UNITARIO_ESPERADO["LB-02-TUB"]
    )


# -------------------------------------------------------------------------------------------
# 2. RF-33, primera mitad: sin condiciones, "Guardar composicion" está deshabilitado
# -------------------------------------------------------------------------------------------


def test_sin_condiciones_el_boton_de_guardar_esta_deshabilitado(monkeypatch, tmp_path):
    """Sin declarar condiciones el boton esta deshabilitado; al declararlas, se habilita (RF-33)."""
    base = tmp_path / "vacia.db"

    at = _pantalla(monkeypatch, base, _filas_de_apu(APU_UI))
    _teclear_cabecera(at, APU_UI)
    at.run()

    assert not at.exception
    assert _por_rotulo(at.button, "Guardar composicion").disabled is True

    at.text_area[0].set_value(CONDICIONES_DE_PRUEBA)
    at.run()

    assert not at.exception
    assert _por_rotulo(at.button, "Guardar composicion").disabled is False


# -------------------------------------------------------------------------------------------
# 3. RF-33, segunda mitad: con condiciones pero sin rendimiento, guardar no persiste nada
# -------------------------------------------------------------------------------------------


def test_sin_rendimiento_guardar_no_persiste_nada(monkeypatch, tmp_path):
    """Condiciones declaradas, rendimiento en blanco: el boton guarda habilitado, pero no guarda."""
    base = tmp_path / "sembrada.db"
    _sembrar_base(base)

    at = _pantalla(monkeypatch, base, _filas_de_apu(APU_UI))
    _teclear_cabecera(at, APU_UI, con_rendimiento=False)
    at.text_area[0].set_value(CONDICIONES_DE_PRUEBA)
    at.run()

    assert not at.exception
    boton = _por_rotulo(at.button, "Guardar composicion")
    assert boton.disabled is False

    boton.click()
    at.run()

    assert not at.exception
    assert at.warning, "se esperaba el aviso de composicion no valida al pulsar guardar"

    with _catalogo_en(base) as catalogo:
        with pytest.raises(KeyError):
            catalogo.partida(CODIGO_UI)


# -------------------------------------------------------------------------------------------
# 4. Guardar dos veces edita la partida (UC-10 crea, UC-11 edita, no duplica)
# -------------------------------------------------------------------------------------------


def test_guardar_dos_veces_edita_la_partida(monkeypatch, tmp_path):
    """La segunda vez que se guarda, con otro rendimiento, edita la partida en vez de duplicarla."""
    base = tmp_path / "sembrada.db"
    _sembrar_base(base)

    at = _pantalla(monkeypatch, base, _filas_de_apu(APU_UI))
    _teclear_cabecera(at, APU_UI)
    at.text_area[0].set_value(CONDICIONES_DE_PRUEBA)
    at.run()
    assert not at.exception

    _por_rotulo(at.button, "Guardar composicion").click()
    at.run()
    assert not at.exception

    # Un rerun de por medio, sin cambiar nada: recien guardada la partida, `_rendimiento()`
    # (ui/paginas/componer.py) pasa de precargar "" (sin historial) a precargar el rendimiento ya
    # persistido ("100"), y ese cambio de precarga cambia el identificador automatico del widget
    # (no tiene `key` explicita). Tecleado y guardado en el mismo rerun donde cambia esa precarga,
    # el valor tecleado quedaria en un widget que este rerun ya dejo atras. Un rerun de asiento
    # deja el identificador estable antes de teclear el segundo rendimiento.
    at.run()
    assert not at.exception

    rendimiento_nuevo = Decimal("120")
    assert rendimiento_nuevo != APU_UI.rendimiento
    _por_rotulo(at.text_input, componer.RENDIMIENTO_ETIQUETA).set_value(_texto(rendimiento_nuevo))
    at.run()
    assert not at.exception

    _por_rotulo(at.button, "Guardar composicion").click()
    at.run()
    assert not at.exception

    with _catalogo_en(base) as catalogo:
        rendimientos = catalogo.rendimientos(CODIGO_UI)

    assert [rendimiento.valor for rendimiento in rendimientos] == [
        APU_UI.rendimiento,
        rendimiento_nuevo,
    ]


# -------------------------------------------------------------------------------------------
# 5. De componer a Excel sin salir de la pantalla (Tarea 2, fase P3)
# -------------------------------------------------------------------------------------------


def test_de_componer_a_excel_desde_la_pantalla(monkeypatch, tmp_path):
    """Guardar, elaborar y auditar: el total del presupuesto y la descarga de Excel, en pantalla."""
    base = tmp_path / "sembrada.db"
    _sembrar_base(base)

    filas = _filas_de_apu(APU_UI)
    filas["componer_cantidades__filas"] = [
        {"codigo_partida": CODIGO_UI, "cantidad": "24", "origen_id": "prueba-ui"}
    ]

    at = _pantalla(monkeypatch, base, filas)
    _teclear_cabecera(at, APU_UI)
    at.text_area[0].set_value(CONDICIONES_DE_PRUEBA)
    at.run()
    assert not at.exception

    _por_rotulo(at.button, "Guardar composicion").click()
    at.run()
    assert not at.exception

    _por_rotulo(at.button, "Elaborar y auditar").click()
    at.run()
    assert not at.exception

    precio_unitario = calcular_apu(APU_UI, PARAMETROS_LINEA_BASE).precio_unitario
    total_esperado = (
        f"{formatear_decimal(Decimal('24') * precio_unitario, DECIMALES_PRESENTACION)} USD"
    )

    assert _por_rotulo(at.metric, "Total del presupuesto").value == total_esperado
    assert len(at.get("download_button")) == 1


# -------------------------------------------------------------------------------------------
# 6. Editar una partida existente (UC-11) no puede borrarle el desglose (auditoria del PR #7)
# -------------------------------------------------------------------------------------------
#
# `DEMO-01-INST` es la partida sembrada por `scripts/seed_demo.py` (caso didactico, CLAUDE.md §1):
# 3 materiales, 2 equipos y 2 lineas de mano de obra (una a jornal y otra a destajo). Estas pruebas
# abren la pantalla **sin** sembrar las tablas: son las que la precarga debe llenar.

CODIGO_DEMO = "DEMO-01-INST"
CLAVES_TABLAS = (
    "componer_materiales__filas",
    "componer_equipos__filas",
    "componer_mano_obra__filas",
)


def _filas_guardadas(base: Path, codigo: str) -> dict[str, list[dict[str, str]]]:
    """Las tres tablas de lo que el catalogo tiene guardado para `codigo`, con los convertidores de
    `tests/integration/test_composicion_extremo_a_extremo.py` (independientes de la pantalla)."""
    with _catalogo_en(base) as catalogo:
        return _filas_de_apu(catalogo.composicion(codigo))


def _cabecera_guardada(base: Path, codigo: str):
    with _catalogo_en(base) as catalogo:
        return catalogo.composicion(codigo)


def _editar_demo(monkeypatch, base: Path, *, unidad: str | None = None) -> AppTest:
    """Teclea el codigo de `DEMO-01-INST` (la precarga ocurre en ese rerun) y luego su cabecera
    registrada (o `unidad`, si se pide otra) y unas condiciones de prueba."""
    guardada = _cabecera_guardada(base, CODIGO_DEMO)
    at = _pantalla(monkeypatch, base, {})
    _por_rotulo(at.text_input, "Codigo").set_value(CODIGO_DEMO)
    at.run()
    assert not at.exception
    _por_rotulo(at.text_input, "Descripcion").set_value(guardada.descripcion)
    unidad_tecleada = unidad if unidad is not None else guardada.unidad
    _por_rotulo(at.text_input, "Unidad").set_value(unidad_tecleada)
    at.text_area[0].set_value(CONDICIONES_DE_PRUEBA)
    at.run()
    assert not at.exception
    return at


def _reemplazar_tablas(at: AppTest, filas: dict[str, list[dict[str, str]]]) -> None:
    """Simula que la persona edita las tablas (`st.data_editor` no se teclea desde `AppTest`): las
    filas nuevas y el borrado de la bitacora de ediciones de cada `st.data_editor`, que es la via
    documentada para imponerle un contenido nuevo (`ui/paginas/componer.py::_tabla_con_busqueda`).
    """
    for clave, valor in filas.items():
        at.session_state[clave] = valor
        widget = clave.removesuffix("__filas")
        if widget in at.session_state:
            del at.session_state[widget]


def test_teclear_el_codigo_de_una_partida_guardada_precarga_sus_tres_tablas(monkeypatch, tmp_path):
    """UC-11, paso 1: las tres tablas de insumos (con la modalidad) llegan precargadas."""
    base = tmp_path / "sembrada.db"
    _sembrar_base(base)
    esperado = _filas_guardadas(base, CODIGO_DEMO)

    at = _pantalla(monkeypatch, base, {})
    for clave in CLAVES_TABLAS:
        assert at.session_state[clave] == [], "antes de teclear el codigo las tablas estan vacias"

    _por_rotulo(at.text_input, "Codigo").set_value(CODIGO_DEMO)
    at.run()
    assert not at.exception

    for clave in CLAVES_TABLAS:
        assert at.session_state[clave] == esperado[clave], clave
    assert {fila["modalidad"] for fila in at.session_state["componer_mano_obra__filas"]} == {
        "jornal",
        "destajo",
    }


def test_guardar_sin_ninguna_linea_sobre_una_partida_existente_no_borra_su_desglose(
    monkeypatch, tmp_path
):
    base = tmp_path / "sembrada.db"
    _sembrar_base(base)
    antes = _filas_guardadas(base, CODIGO_DEMO)

    at = _editar_demo(monkeypatch, base)
    _reemplazar_tablas(at, {clave: [] for clave in CLAVES_TABLAS})
    at.run()
    assert not at.exception

    _por_rotulo(at.button, "Guardar composicion").click()
    at.run()
    assert not at.exception

    assert at.error, "se esperaba un error al guardar una composicion sin lineas"
    assert "ninguna linea" in at.error[0].value
    assert not at.success
    assert _filas_guardadas(base, CODIGO_DEMO) == antes


def test_guardar_con_otra_unidad_sobre_una_partida_existente_no_la_cambia(monkeypatch, tmp_path):
    base = tmp_path / "sembrada.db"
    _sembrar_base(base)
    antes = _filas_guardadas(base, CODIGO_DEMO)
    unidad_registrada = _cabecera_guardada(base, CODIGO_DEMO).unidad

    at = _editar_demo(monkeypatch, base, unidad="m2")
    _por_rotulo(at.button, "Guardar composicion").click()
    at.run()
    assert not at.exception

    assert at.error, "se esperaba un error al guardar con otra unidad"
    assert repr(unidad_registrada) in at.error[0].value
    assert not at.success
    assert _cabecera_guardada(base, CODIGO_DEMO).unidad == unidad_registrada
    assert _filas_guardadas(base, CODIGO_DEMO) == antes


def test_editar_una_cantidad_y_guardar_reemplaza_la_composicion(monkeypatch, tmp_path):
    """El flujo normal de UC-11 sigue funcionando: precarga, se cambia una cantidad y se guarda."""
    base = tmp_path / "sembrada.db"
    _sembrar_base(base)
    filas = _filas_guardadas(base, CODIGO_DEMO)
    filas["componer_equipos__filas"][0]["cantidad"] = "2"

    at = _editar_demo(monkeypatch, base)
    _reemplazar_tablas(at, {"componer_equipos__filas": filas["componer_equipos__filas"]})
    at.run()
    assert not at.exception

    _por_rotulo(at.button, "Guardar composicion").click()
    at.run()
    assert not at.exception

    assert not at.error
    assert at.success
    assert _filas_guardadas(base, CODIGO_DEMO) == filas
