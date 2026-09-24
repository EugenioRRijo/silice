from pathlib import Path

import pytest

from tests.fixtures import apu_linea_base as linea_base

pytest.importorskip("ifcopenshell")

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "tanquilla.ifc"


def test_g1_lo_extraido_coincide_con_el_calculo_manual():
    from adapters.civil.ifc import AdaptadorCivilIFC

    items = AdaptadorCivilIFC().extraer(MUESTRA)
    assert len(items) == 1
    item = items[0]
    concreto = linea_base.APU_CONCRETO.codigo_partida
    # (0.8^2 - 0.6^2) * 0.8: la memoria de calculo de la linea base, por tanquilla
    assert item.cantidad == linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA[concreto]
    assert item.unidad == "m3" and item.codigo_partida == concreto
    assert item.origen_tipo.value == "ifc" and len(item.origen_id) == 22  # GlobalId IFC


def test_dos_cantidades_del_mismo_tipo_ifc_son_ambiguas(tmp_path):
    """Dos `IfcQuantityVolume` en el mismo elemento: el adaptador no debe elegir una en silencio
    sino fallar ruidosamente con archivo y GlobalId (rama declarada en `_cantidad_desde_qto`,
    sin fixture que la ejercitara hasta esta sesion — bitacora F.1).
    """
    import ifcopenshell
    import ifcopenshell.guid

    from adapters.civil.ifc import AdaptadorCivilIFC
    from scripts.generar_tanquilla_ifc import generar

    ruta = tmp_path / "tanquilla_doble.ifc"
    generar(ruta)
    modelo = ifcopenshell.open(str(ruta))
    elemento = modelo.by_type("IfcBuildingElementProxy")[0]
    # Un segundo IfcElementQuantity con otro IfcQuantityVolume para el mismo elemento, como los
    # que exportan herramientas BIM que declaran volumen neto y bruto por separado.
    volumen_bruto = modelo.create_entity(
        "IfcQuantityVolume", Name="VolumenBruto", VolumeValue=0.512
    )
    conjunto = modelo.create_entity(
        "IfcElementQuantity",
        GlobalId=ifcopenshell.guid.new(),
        Name="Qto_Otro",
        Quantities=[volumen_bruto],
    )
    modelo.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[elemento],
        RelatingPropertyDefinition=conjunto,
    )
    modelo.write(str(ruta))

    with pytest.raises(ValueError, match="ambigua"):
        AdaptadorCivilIFC().extraer(ruta)
