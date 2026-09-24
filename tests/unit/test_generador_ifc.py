from decimal import Decimal

import pytest

from tests.fixtures import apu_linea_base as linea_base

pytest.importorskip("ifcopenshell")


def test_genera_una_tanquilla_con_pset_y_volumen(tmp_path):
    import ifcopenshell
    import ifcopenshell.util.element

    from scripts.generar_tanquilla_ifc import generar

    ruta = tmp_path / "tanquilla.ifc"
    geometria = linea_base.GEOMETRIA_TANQUILLA
    generar(ruta, a=geometria["a"], h=geometria["h"], e=geometria["e"])
    modelo = ifcopenshell.open(str(ruta))
    elementos = modelo.by_type("IfcBuildingElementProxy")
    assert len(elementos) == 1
    psets = ifcopenshell.util.element.get_psets(elementos[0])
    apu = psets["Pset_APU"]
    concreto = linea_base.APU_CONCRETO.codigo_partida
    assert apu["COVENIN_Codigo"] == concreto and apu["Unidad"] == "m3"
    qto = psets["Qto_APU"]
    assert Decimal(str(qto["VolumenConcreto"])) == (
        linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA[concreto]
    )
    assert elementos[0].GlobalId
