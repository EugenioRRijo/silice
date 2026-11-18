"""Los porcentajes del libro que se lleva a la Hoja (`aplicacion.libro_a_la_hoja`, sin la API).

La Hoja lleva un solo juego de parámetros por obra: si las hojas del libro usan juegos distintos,
`PorcentajesDistintos` dice en qué se apartan. Aquí, el bono de alimentación (un monto diario, no
un porcentaje) y la frase cuando ningún campo rotulado difiere.

Oráculos a mano: los textos se escriben aquí desde el patrón del mensaje de la prueba de punta a
punta (`tests/integration/test_api_hoja_libro.py`), con coma decimal; ninguno se lee del módulo.
Datos ficticios: hojas «APU 1» a «APU 3» con parámetros construidos.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from aplicacion import libro_a_la_hoja
from aplicacion.libro_a_la_hoja import ApuDelLibro, PorcentajesDistintos
from core.contracts.apu import ParametrosCosto

D = Decimal


def _apu(hoja: str, **parametros: Decimal) -> ApuDelLibro:
    # `_porcentajes` solo lee la hoja y los parámetros: la composición no hace falta aquí.
    return ApuDelLibro(
        hoja=hoja,
        numero=None,
        composicion=None,  # type: ignore[arg-type]
        parametros=ParametrosCosto(**parametros),
        precio_impreso=D(0),
    )


def test_dos_hojas_que_solo_difieren_en_el_bono_lo_nombran() -> None:
    apus = [
        _apu("APU 1", bono_alimentacion=D("0")),
        _apu("APU 2", bono_alimentacion=D("0")),
        _apu("APU 3", bono_alimentacion=D("1500.50")),
    ]
    with pytest.raises(PorcentajesDistintos) as error:
        libro_a_la_hoja._porcentajes(apus)
    assert str(error.value) == (
        "Las hojas del libro no usan los mismos porcentajes y la Hoja lleva uno solo por obra: "
        "APU 3 usa un bono de alimentación de 1.500,5 y las demás de 0."
    )


def test_si_ningun_campo_rotulado_difiere_el_mensaje_no_se_rompe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un campo de `ParametrosCosto` que `_CAMPOS` no rotule (uno que se agregue mañana) no deja la
    frase sin nada que nombrar: dice que esas hojas usan otros parámetros de costo."""
    monkeypatch.setattr(
        libro_a_la_hoja,
        "_CAMPOS",
        tuple(c for c in libro_a_la_hoja._CAMPOS if c[0] != "bono_alimentacion"),
    )
    apus = [_apu("APU 1", bono_alimentacion=D("0")), _apu("APU 2", bono_alimentacion=D("5"))]
    with pytest.raises(PorcentajesDistintos) as error:
        libro_a_la_hoja._porcentajes(apus)
    assert str(error.value) == (
        "Las hojas del libro no usan los mismos porcentajes y la Hoja lleva uno solo por obra: "
        "APU 2 usa otros parámetros de costo que las demás."
    )


@pytest.mark.parametrize(
    ("fraccion", "esperado"),
    [
        (Decimal("0.05"), "5"),
        (Decimal("0.125"), "12,5"),
        # Con punto de miles, como toda cifra que ve la persona (`texto_de_cifra`).
        (Decimal("12.5"), "1.250"),
        (Decimal("-0"), "0"),
    ],
)
def test_pct_escribe_la_cifra_con_coma_y_punto_de_miles(fraccion, esperado):
    assert libro_a_la_hoja._pct(fraccion) == esperado
