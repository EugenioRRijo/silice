from decimal import Decimal
from pathlib import Path

import pytest

from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_civil import CODIGOS

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


def test_uc04_2a_un_objeto_ifc_no_se_recalcula_por_reglas():
    """UC-04, flujo 2a: la fuente es un modelo, no reglas; se exige reimportarlo."""
    from adapters.civil.ifc import AdaptadorCivilIFC
    from adapters.civil.recalculo import recalcular

    items = AdaptadorCivilIFC().extraer(MUESTRA)

    with pytest.raises(ValueError, match="reimporte el modelo"):
        recalcular(items, {items[0].origen_id: {"a": Decimal("1.00")}}, CODIGOS)


def test_uc04_2a_reimportar_empareja_por_global_id(tmp_path):
    """UC-04, flujo 2a: al reimportar, la correspondencia de las partidas se conserva por GlobalId.
    Un modelo generado de nuevo tiene otro GlobalId: no es el mismo objeto y no se empareja."""
    import ifcopenshell

    from adapters.civil.ifc import AdaptadorCivilIFC
    from adapters.civil.recalculo import emparejar
    from scripts.generar_tanquilla_ifc import generar

    version_1 = tmp_path / "v1.ifc"
    generar(version_1)
    modelo = ifcopenshell.open(str(version_1))
    (volumen,) = modelo.by_type("IfcQuantityVolume")
    volumen.VolumeValue = 0.3
    version_2 = tmp_path / "v2.ifc"
    modelo.write(str(version_2))
    otro = tmp_path / "otro.ifc"
    generar(otro)

    adaptador = AdaptadorCivilIFC()
    anteriores = adaptador.extraer(version_1)
    nuevos = adaptador.extraer(version_2)
    ajenos = adaptador.extraer(otro)

    emparejamiento = emparejar(anteriores, nuevos)
    ((anterior, nuevo),) = emparejamiento.pares
    concreto = linea_base.APU_CONCRETO.codigo_partida
    assert anterior.origen_id == nuevo.origen_id
    assert anterior.cantidad == linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA[concreto]
    assert nuevo.cantidad == Decimal("0.3")
    assert emparejamiento.solo_anteriores == () and emparejamiento.solo_nuevos == ()

    sin_par = emparejar(anteriores, ajenos)
    assert sin_par.pares == ()
    assert sin_par.solo_anteriores == tuple(anteriores)
    assert sin_par.solo_nuevos == tuple(ajenos)
