"""INV-083 en la interfaz: los escenarios de un base con pendientes los declaran (UC-08, UC-01 3a).

`generar_escenario` reelabora solo los renglones valorados, asi que un escenario sobre un base
con items pendientes no los ve. La pagina carga el base con `cargar_elaboracion` (INV-080) y
declara sus pendientes con un aviso; el informe del propio escenario y la ruta de la API quedan
en el dictamen C3-12. La base vive en `tmp_path`, desviada por el objeto modulo
`sys.modules["ui.caso"]`; la salvaguarda de `tests/conftest.py` vigila `data/apu.db`.
"""

from __future__ import annotations

import importlib
from decimal import Decimal
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.budget import elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from scripts.seed import sembrar
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import items_auditados

SCRIPT = "from ui.paginas.escenarios import render\nrender()\n"
ROTULO_GENERAR = "Generar escenario"
#: Nombre por defecto del primer escenario que propone la pagina.
NOMBRE_ESCENARIO = "escenario 1"

PENDIENTE_T99 = ItemComputo(
    codigo_partida="XX-99-NUE",
    descripcion="Excavacion de un foso nuevo",
    unidad="m3",
    cantidad=Decimal("2.5"),
    origen_id="T-99",
    origen_tipo=OrigenTipo.MANUAL,
    dominio=Dominio.CIVIL,
)


def _base_con_pendiente(ruta: Path) -> None:
    """001 con la linea base mas T-99, guardado con su pendiente por el nucleo directo."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            resultado = elaborar(
                [*items_auditados(), PENDIENTE_T99],
                catalogo.composiciones(
                    linea_base.CODIGOS_LINEA_BASE, fecha=linea_base.FECHA_LINEA_BASE
                ),
                linea_base.PARAMETROS_LINEA_BASE,
                codigo=linea_base.CODIGO_PRESUPUESTO,
                fecha=linea_base.FECHA_LINEA_BASE,
                moneda=linea_base.MONEDA,
                plan=plan_secuencial,
            )
            assert resultado.pendientes == (PENDIENTE_T99,)
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                parametros=linea_base.PARAMETROS_LINEA_BASE,
                pendientes=resultado.pendientes,
            )
            sesion.commit()
    finally:
        motor.dispose()


def test_el_escenario_de_un_base_con_pendientes_los_declara(monkeypatch, tmp_path):
    base = tmp_path / "caso.db"
    _base_con_pendiente(base)
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
