"""INV-083 en la interfaz: los escenarios de un base con pendientes los declaran (UC-08, UC-01 3a).

`generar_escenario` reelabora solo los renglones valorados, asi que un escenario sobre un base
con items pendientes no los ve. La pagina carga el base con `cargar_elaboracion` (INV-080) y
declara sus pendientes con un aviso. La ruta de la API los declara desde C4
(`tests/integration/test_api_escenarios.py`); el informe del propio escenario no, y queda en
limitaciones (ruling C4-3). La base vive en `tmp_path` (`tests/fixtures/base_con_pendiente.py`),
desviada por el objeto modulo `sys.modules["ui.caso"]`; la salvaguarda de `tests/conftest.py`
vigila `data/apu.db`.
"""

from __future__ import annotations

import importlib

from streamlit.testing.v1 import AppTest

from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.base_con_pendiente import guardar_base_con_pendiente

SCRIPT = "from ui.paginas.escenarios import render\nrender()\n"
ROTULO_GENERAR = "Generar escenario"
#: Nombre por defecto del primer escenario que propone la pagina.
NOMBRE_ESCENARIO = "escenario 1"


def test_el_escenario_de_un_base_con_pendientes_los_declara(monkeypatch, tmp_path):
    base = tmp_path / "caso.db"
    guardar_base_con_pendiente(base)
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    antes = huella(RUTA_BASE_REAL)

    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    next(b for b in at.button if b.label == ROTULO_GENERAR).click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    avisos = [w.value for w in at.warning]
    assert any(
        "T-99" in aviso and "XX-99-NUE" in aviso and "no suman" in aviso for aviso in avisos
    ), avisos
    # Oraculo de la fixture: el base valorado es la linea base, y el escenario con los parametros
    # por defecto (los del base) no la cambia.
    total = formatear_decimal(linea_base.TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION)
    # La tabla de RF-31 es la primera con columna `escenario` (el editor de precios va antes).
    tabla = next(d.value for d in at.dataframe if "escenario" in d.value.columns)
    fila = tabla[tabla["escenario"] == NOMBRE_ESCENARIO]
    assert list(fila["total"]) == [total]
    assert huella(RUTA_BASE_REAL) == antes


def test_el_escenario_base_de_una_version_editada_en_la_hoja_cuadra_con_su_presupuesto(
    monkeypatch, tmp_path
):
    """SF3: la pagina toma las composiciones de la instantanea de la version, no del catalogo."""
    from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
    from scripts.seed import sembrar
    from tests.fixtures.versiones import editar_apu_en_la_hoja, elaborar_001, guardar_001

    base = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        guardar_001(sesion, sembrar(sesion), elaborar_001(sesion))
        sesion.commit()
        total = editar_apu_en_la_hoja(sesion, Catalogo(sesion)).total
    motor.dispose()
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))

    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.run()
    elegido = next(o for o in at.selectbox[0].options if o.endswith("/ 002"))
    at.selectbox[0].select(elegido).run()
    next(b for b in at.button if b.label == ROTULO_GENERAR).click().run()

    assert not at.exception, [e.value for e in at.exception]
    exacto = formatear_decimal(total, DECIMALES_PRESENTACION)
    tabla = next(d.value for d in at.dataframe if "escenario" in d.value.columns)
    assert list(tabla[tabla["escenario"] == NOMBRE_ESCENARIO]["total"]) == [exacto]
