"""A qué valuación pertenece cada hallazgo de R13 y R14 (hallazgo 4 de la depuración 2026-11-20).

El núcleo cita en `origen_ids` la valuación (`valuacion:<número>` o `valuacion:<número>:<código>`)
y, en R13(c), solo el origen de la partida no programada, que no trae ese prefijo. La columna
Estado de las valuaciones y la columna Valuación de los hallazgos leen el mismo número con un solo
ayudante, cotejado contra las valuaciones registradas: un número puede llevar «:» por dentro.
Datos ficticios.
"""

from __future__ import annotations

from types import SimpleNamespace

from aplicacion.control_hallazgos import hallazgos_de_valuaciones
from aplicacion.control_tablas import estado_de_valuaciones


def _hallazgo(origenes: tuple[str, ...], severidad: str = "ADVERTENCIA", regla: str = "R13"):
    return SimpleNamespace(
        origen_ids=origenes,
        regla=regla,
        severidad=SimpleNamespace(name=severidad),
        # La columna Estado dice «<Severidad>: <mensaje> (<regla>)»; `mensaje_de_hallazgo` vuelve
        # «x» en «X.» (mayúscula inicial y punto final).
        descripcion="x",
    )


def _resultado(*hallazgos, valuaciones: tuple[str, ...] = ("1",)):
    return SimpleNamespace(
        informe=SimpleNamespace(hallazgos=list(hallazgos)),
        instantanea=SimpleNamespace(valuaciones=[SimpleNamespace(clave=c) for c in valuaciones]),
    )


def test_un_hallazgo_de_partida_sin_dos_puntos_no_revienta_ni_marca_valuaciones() -> None:
    # R13(c) con un origen de modelo o escrito a mano que no lleva «:».
    resultado = _resultado(_hallazgo(("2O2Fr$t4X7Zf8NOew3FLOH",)))
    assert estado_de_valuaciones(resultado) == {}
    assert hallazgos_de_valuaciones(resultado)[0]["Valuacion"] == ""


def test_una_partida_a_mano_no_se_imputa_a_la_valuacion_del_mismo_numero() -> None:
    resultado = _resultado(_hallazgo(("a-mano:1",)))
    assert estado_de_valuaciones(resultado) == {}
    assert hallazgos_de_valuaciones(resultado)[0]["Valuacion"] == ""


def test_un_numero_de_valuacion_con_dos_puntos_se_lee_entero() -> None:
    resultado = _resultado(
        _hallazgo(("valuacion:VAL:01:P-01", "a-mano:1"), severidad="ERROR"),
        _hallazgo(("valuacion:VAL:01",), regla="R14"),
        valuaciones=("VAL", "VAL:01"),
    )
    assert estado_de_valuaciones(resultado) == {"VAL:01": "Error: X. (R13)"}
    assert [f["Valuacion"] for f in hallazgos_de_valuaciones(resultado)] == ["VAL:01", "VAL:01"]


def test_un_numero_solo_casa_entero_o_seguido_de_dos_puntos() -> None:
    resultado = _resultado(
        _hallazgo(("valuacion:VAL:P-01",)),
        valuaciones=("VAL", "VAL:P"),
    )
    # «valuacion:VAL:P-01» es la línea P-01 de VAL; no hay valuación «VAL:P-01».
    assert estado_de_valuaciones(resultado) == {"VAL": "Advertencia: X. (R13)"}


def test_el_caso_de_siempre_sigue_igual() -> None:
    resultado = _resultado(
        _hallazgo(("valuacion:2:P-01",), severidad="ADVERTENCIA"),
        _hallazgo(("valuacion:2",), severidad="ERROR", regla="R14"),
        _hallazgo(("valuacion:1:P-02",), severidad="INFO"),
        valuaciones=("1", "2"),
    )
    assert estado_de_valuaciones(resultado) == {
        "2": "Error: X. (R14)",
        "1": "Información: X. (R13)",
    }
