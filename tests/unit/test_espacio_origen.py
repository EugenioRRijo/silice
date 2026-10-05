"""Orígenes de la medida (spec §6.3 y RF-44): referencia obligatoria por tipo."""

from __future__ import annotations

import pytest

from adapters.espacio import OrigenMedida, TipoOrigen

VALIDOS = [
    (TipoOrigen.PLANO, {"plano": "A-01", "lamina": "2", "revision": "B"}),
    (TipoOrigen.DXF, {"archivo": "of001.dxf", "capa": "AMB-OF001", "handle": "2F"}),
    (TipoOrigen.IFC, {"archivo": "of001.ifc", "global_id": "0xYz12"}),
    (TipoOrigen.LEVANTAMIENTO, {"fecha": "2026-10-04", "responsable": "Eugenio"}),
    (TipoOrigen.SUPUESTO, {"motivo": "ejemplo de memoria de cálculo"}),
]


@pytest.mark.parametrize(("tipo", "referencia"), VALIDOS)
def test_cada_tipo_con_su_referencia_completa_es_valido(tipo, referencia):
    origen = OrigenMedida(id="O", tipo=tipo, referencia=referencia)
    assert dict(origen.referencia) == referencia


@pytest.mark.parametrize(("tipo", "referencia"), VALIDOS)
def test_un_origen_completo_no_esta_incompleto(tipo, referencia):
    origen = OrigenMedida(id="O", tipo=tipo, referencia=referencia)
    assert origen.faltantes == () and not origen.incompleto


@pytest.mark.parametrize(("tipo", "referencia"), VALIDOS)
def test_falta_un_dato_de_la_referencia_el_origen_se_acepta_y_queda_incompleto(tipo, referencia):
    """RF-44 / UC-13a: la referencia faltante no se rechaza; R8 la marca ERROR."""
    for clave in referencia:
        incompleta = {k: v for k, v in referencia.items() if k != clave}
        origen = OrigenMedida(id="O", tipo=tipo, referencia=incompleta)
        assert origen.incompleto
        assert origen.faltantes == (clave,)


@pytest.mark.parametrize(("tipo", "referencia"), VALIDOS)
def test_un_dato_en_blanco_cuenta_como_faltante(tipo, referencia):
    for clave in referencia:
        en_blanco = dict(referencia) | {clave: "   "}
        origen = OrigenMedida(id="O", tipo=tipo, referencia=en_blanco)
        assert origen.faltantes == (clave,)


def test_un_origen_sin_ninguna_referencia_lista_todo_lo_que_falta():
    origen = OrigenMedida(id="O", tipo=TipoOrigen.PLANO, referencia={})
    assert origen.faltantes == ("plano", "lamina", "revision")


def test_el_id_no_puede_estar_vacio():
    with pytest.raises(ValueError, match="id"):
        OrigenMedida(id=" ", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "m"})


def test_el_tipo_debe_ser_un_tipo_de_origen():
    with pytest.raises(ValueError):
        OrigenMedida(id="O", tipo="inventado", referencia={"motivo": "m"})  # type: ignore[arg-type]


def test_solo_el_supuesto_es_advertencia():
    assert OrigenMedida(id="O", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "m"}).es_supuesto
    assert not OrigenMedida(
        id="O", tipo=TipoOrigen.LEVANTAMIENTO, referencia={"fecha": "f", "responsable": "r"}
    ).es_supuesto


def test_la_referencia_es_inmutable_y_el_origen_hashable():
    origen = OrigenMedida(id="O", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "m"})
    hash(origen)
    assert origen == OrigenMedida(id="O", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "m"})
