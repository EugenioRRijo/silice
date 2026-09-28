import sys
from pathlib import Path

import pytest

from tests.fixtures.sin_extra import SinExtra

pytest.importorskip("ifcopenshell")

MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "tanquilla.ifc"

#: Modulos que un import perezoso mal hecho dejaria en el cache con ifcopenshell ya cargado; se
#: limpian antes y se restauran despues de simular su ausencia (`tests.fixtures.sin_extra`).
_MODULOS_RELACIONADOS_CON_IFC = (
    "ifcopenshell",
    "ifcopenshell.geom",
    "ifcopenshell.util",
    "ifcopenshell.util.element",
    "adapters.civil.ifc",
    "ui.visor3d",
    "ui.paginas.visor",
    "ui.app",
)


def test_la_tanquilla_se_tesela_a_una_malla_valida():
    from ui.visor3d import mallas

    resultado = mallas(MUESTRA)
    assert len(resultado) == 1
    malla = resultado[0]
    assert len(malla["vertices"]) % 3 == 0 and len(malla["vertices"]) >= 24
    assert len(malla["caras"]) % 3 == 0 and malla["caras"]
    assert malla["global_id"]


def test_ui_app_y_el_visor_se_importan_sin_ifcopenshell(monkeypatch):
    """`ui.app` registra seis paginas; antes de esta tarea ninguna requeria el extra `civil`. Este
    fix debe mantener esa propiedad: importar `ui.app` (y por lo tanto `ui.paginas.visor` y
    `ui.visor3d`) no debe requerir ifcopenshell, solo usarlo cuando el visor se ejecuta de verdad.
    """
    import importlib

    with SinExtra(monkeypatch, ("ifcopenshell",), _MODULOS_RELACIONADOS_CON_IFC):
        modulo_app = importlib.import_module("ui.app")
        modulo_visor = importlib.import_module("ui.paginas.visor")
        modulo_3d = importlib.import_module("ui.visor3d")

    # INV-024: `is not None` no afirma nada (import_module nunca devuelve None); se exige que cada
    # modulo exponga su punto de entrada. Que el extra no se cargue lo afirma
    # `tests/unit/test_extras_perezosos.py`, en un proceso limpio.
    assert callable(modulo_app.main)
    assert callable(modulo_visor.render)
    assert callable(modulo_3d.mallas)


def test_el_gestor_deja_sincronizado_el_atributo_del_paquete(monkeypatch):
    """INV-021: al salir del gestor, el atributo `visor` del paquete `ui.paginas` apunta al mismo
    modulo que `sys.modules`, no a la copia fria importada sin el extra (si no, un
    `monkeypatch.setattr("ui.paginas.visor.X", ...)` posterior parcharia la copia huerfana)."""
    import importlib

    importlib.import_module("ui.paginas.visor")
    with SinExtra(monkeypatch, ("ifcopenshell",), _MODULOS_RELACIONADOS_CON_IFC):
        importlib.import_module("ui.paginas.visor")

    assert sys.modules["ui.paginas"].visor is sys.modules["ui.paginas.visor"]


def test_cargar_dependencias_civiles_reporta_la_ausencia_del_extra(monkeypatch):
    """Sin ifcopenshell, el cargador perezoso de `ui.paginas.visor` relanza `ImportError` (que
    `render()` convierte en un mensaje con `st.error`, no en una traza cruda)."""
    from ui.paginas import visor

    with SinExtra(monkeypatch, ("ifcopenshell",), _MODULOS_RELACIONADOS_CON_IFC):
        with pytest.raises(ImportError):
            visor._cargar_dependencias_civiles()


def test_cargar_dependencias_civiles_funciona_con_el_extra_instalado():
    """Con el extra `civil` instalado (el caso normal del sprint), el cargador perezoso sí entrega
    ifcopenshell y `AdaptadorCivilIFC` utilizables."""
    from ui.paginas import visor

    ifcopenshell, adaptador_civil_ifc = visor._cargar_dependencias_civiles()

    assert ifcopenshell.version
    assert adaptador_civil_ifc.dominio.value == "civil"
