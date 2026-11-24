"""Toda constante vial cuya fuente empieza por «supuesto declarado» se reconoce como supuesto,
aunque lleve una nota pegada («; a cotejar con la ficha del producto»)."""

from __future__ import annotations

from adapters.vial import constantes as c


def _constantes() -> list[c.Constante]:
    return [v for v in vars(c).values() if isinstance(v, c.Constante)]


def test_las_ocho_constantes_supuestas_se_reconocen_aunque_lleven_nota() -> None:
    supuestas = [k for k in _constantes() if k.fuente.startswith(c.SUPUESTO_DECLARADO)]
    assert len(supuestas) == 8
    assert all(k.supuesto_declarado for k in supuestas), [
        k.id for k in supuestas if not k.supuesto_declarado
    ]


def test_una_constante_con_fuente_normativa_no_es_supuesto() -> None:
    assert not c.FUENTE_CODIGOS_VIALES.supuesto_declarado
    normativa = c.Constante("X", "x", "1", "COVENIN 2000; supuesto declarado en otra")
    assert not normativa.supuesto_declarado
