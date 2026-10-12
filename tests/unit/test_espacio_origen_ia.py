"""Origen «propuesta de IA» y su lectura en R8 (S4 §5.4, RS4-4; plan 0.9.0, tarea 4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from adapters.espacio import Ambiente, Espacio, OrigenMedida, TipoOrigen
from adapters.espacio.origen import REFERENCIA_OBLIGATORIA, supuestos_de_ia
from adapters.espacio.reglas import OrigenDeLaMedida
from core.contracts import Severidad
from core.contracts.presupuesto import Presupuesto

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())
BASE = {"proveedor": "claude", "modelo": "claude-opus-5-5", "sesion": "7", "propuesta": "3"}


def _espacio(referencia: dict[str, str]) -> Espacio:
    origen = OrigenMedida(id="IA-7-3", tipo=TipoOrigen.IA, referencia=referencia)
    ambiente = Ambiente(
        id="BAN-01",
        nombre="Bano",
        x0=D("0"),
        y0=D("0"),
        largo=D("2"),
        ancho=D("1.5"),
        alto=D("2.5"),
        origen_id="IA-7-3",
    )
    return Espacio(origenes=(origen,), ambientes=(ambiente,))


def _r8(espacio: Espacio):
    return OrigenDeLaMedida(espacio).evaluar(VACIO)


def test_la_referencia_obligatoria_del_origen_ia_son_cuatro_datos():
    assert REFERENCIA_OBLIGATORIA[TipoOrigen.IA] == ("proveedor", "modelo", "sesion", "propuesta")


def test_un_origen_ia_completo_y_sin_supuestos_no_da_hallazgo():
    assert _r8(_espacio(BASE)) == []


def test_cada_campo_supuesto_es_una_advertencia_exacta():
    referencia = {**BASE, "supuesto.x0": "esquina del bano en el origen", "supuesto.y0": "idem"}
    hallazgos = _r8(_espacio(referencia))
    assert [(h.regla, h.severidad, h.origen_ids, h.descripcion) for h in hallazgos] == [
        (
            "R8",
            Severidad.ADVERTENCIA,
            ("esp_ambientes:BAN-01",),
            "ambiente BAN-01: alto supuesto por la IA: x0 (esquina del bano en el origen) "
            "(origen IA-7-3)",
        ),
        (
            "R8",
            Severidad.ADVERTENCIA,
            ("esp_ambientes:BAN-01",),
            "ambiente BAN-01: alto supuesto por la IA: y0 (idem) (origen IA-7-3)",
        ),
    ]


@pytest.mark.parametrize("falta", sorted(BASE))
def test_una_referencia_incompleta_es_error_y_no_lista_supuestos(falta):
    referencia = {k: v for k, v in BASE.items() if k != falta} | {"supuesto.x0": "m"}
    hallazgos = _r8(_espacio(referencia))
    assert [(h.severidad, h.descripcion) for h in hallazgos] == [
        (
            Severidad.ERROR,
            f"ambiente BAN-01: origen sin referencia (origen IA-7-3: falta «{falta}»)",
        )
    ]


def test_supuestos_de_ia_devuelve_pares_ordenados_y_solo_para_la_ia():
    origen = OrigenMedida(
        id="O", tipo=TipoOrigen.IA, referencia={**BASE, "supuesto.z": "b", "supuesto.x0": "a"}
    )
    assert supuestos_de_ia(origen) == (("x0", "a"), ("z", "b"))
    otro = OrigenMedida(id="S", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "m"})
    assert supuestos_de_ia(otro) == ()
