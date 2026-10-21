"""El informe de la importacion en `aplicacion.hoja_plano` (T10, 3e-2): mismas filas que la clasica,
en tiempo lineal.

`filas_del_informe` de la clasica (`ui/hoja.py`, copiada tal cual en `aplicacion/hoja.py`) quita las
referencias internas `(SF5-1, SF5-2)` con `re.sub(r"\\s*\\((?:SF\\d+-\\d+(?:,\\s*)?)+\\)", ...)`. El
`\\s*` del principio hace la sustitucion CUADRATICA en una corrida larga de espacios: medido en este
equipo, 100 000 espacios en un mensaje tardan decenas de segundos. El mensaje sale del plano subido
(capas, textos), asi que un DXF hostil lo puede provocar dentro del tope de 20 MiB. La API usa una
version lineal (`hoja_plano.filas_del_informe`) que da EXACTAMENTE las mismas filas: esta prueba lo
fija contra `ui.hoja` VIVO y mide el caso hostil.

Oraculos a mano: el texto esperado de cada caso esta escrito aqui (quitar la referencia y los
espacios que la preceden, nada mas).
"""

from __future__ import annotations

import time

import pytest

from adapters.espacio.planos import ItemInforme, TipoItem
from aplicacion import hoja_plano
from tests.fixtures.planos_de_la_hoja import DXF_OF001
from ui import hoja as clasica

CLAVES = ("tipo", "referencia", "fila", "mensaje")

CASOS = [
    ("", ""),
    ("sin referencias", "sin referencias"),
    ("texto (SF5-1, SF5-2)", "texto"),
    ("a  (SF1-2)b", "ab"),
    ("(SF1-1)", ""),
    ("x (SF1-1)(SF2-2) y", "x y"),
    ("x\t\n(SF3-4,  SF3-5) fin", "x fin"),
    ("( SF1-1) queda", "( SF1-1) queda"),
    ("(SF1-) queda", "(SF1-) queda"),
    ("(SF1-1 sin cerrar", "(SF1-1 sin cerrar"),
    ("  (SF1-1)  ", "  "),
    ("a (SF1-1)", "a"),
    ("a\x1c(SF1-1)", "a"),
    ("a (SF1-1, ) b", "a b"),
    ("a (SF12-345,SF6-7) b (SF8-9)", "a b"),
    ("(sf1-1) minusculas", "(sf1-1) minusculas"),
]


def _item(mensaje: str) -> ItemInforme:
    return ItemInforme(TipoItem.APROXIMADO, "esp_puntos", "H1", "P1", mensaje)


def _como_la_clasica(items) -> list[dict[str, str]]:
    return [dict(zip(CLAVES, f.values(), strict=True)) for f in clasica.filas_del_informe(items)]


@pytest.mark.parametrize(("mensaje", "esperado"), CASOS)
def test_cada_mensaje_queda_como_en_la_clasica(mensaje, esperado) -> None:
    (fila,) = hoja_plano.filas_del_informe([_item(mensaje)])
    assert fila == {"tipo": "Aproximado", "referencia": "H1", "fila": "P1", "mensaje": esperado}
    assert [fila] == _como_la_clasica([_item(mensaje)])


def test_el_informe_del_dxf_de_of001_es_el_de_la_clasica() -> None:
    informe = clasica.leer_plano(DXF_OF001).informe
    assert hoja_plano.filas_del_informe(informe) == _como_la_clasica(informe)
    assert len(informe) > 30


@pytest.mark.parametrize(
    ("mensaje", "esperado"),
    [
        (" " * 100_000, " " * 100_000),
        (" " * 100_000 + "(SF1-1)", ""),
        ("x" + " " * 100_000 + "(x", "x" + " " * 100_000 + "(x"),
        ("(SF1-1, " * 14_000, "(SF1-1, " * 14_000),
        (" (SF1-1)" * 12_500, ""),
    ],
    ids=["espacios", "espacios-y-referencia", "espacios-y-parentesis", "sin-cierre", "muchas"],
)
def test_un_mensaje_hostil_de_100_000_caracteres_tarda_menos_de_un_segundo(
    mensaje, esperado
) -> None:
    inicio = time.perf_counter()
    (fila,) = hoja_plano.filas_del_informe([_item(mensaje)])
    assert time.perf_counter() - inicio < 1
    assert fila["mensaje"] == esperado
