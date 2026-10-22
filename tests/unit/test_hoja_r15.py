"""R15 en la hoja en vivo (spec S3 §3.4): se evalúa con R8 a R10 al elaborar el borrador.

La hoja no pasa por la reauditoría del paquete: usa las mismas reglas del espacio, y R15 es una
de ellas desde la 0.8.0. Las fronteras de R15 las prueba `test_r15_geometria_plano`."""

from __future__ import annotations

from datetime import date

from aplicacion import hoja
from core.contracts.verificacion import Severidad
from tests.fixtures.espacio_minimo import ambiente, espacio
from tests.fixtures.espacio_of001 import espacio_of001


def _r15(resultado) -> list:
    return [h for h in resultado.elaboracion.informe.hallazgos if h.regla == "R15"]


def _elaborar(un_espacio):
    return hoja.elaborar_hoja(un_espacio, {}, codigo="H-R15", fecha=date(2026, 11, 1))


def test_dos_ambientes_que_se_superponen_dan_un_error_de_r15_en_el_informe_de_la_hoja() -> None:
    a = ambiente("A", largo="1", ancho="1")
    b = ambiente("B", x0="0.9899", largo="1", ancho="1")  # 0,0101 m2 de superposición
    [hallazgo] = _r15(_elaborar(espacio([a, b])))
    assert hallazgo.severidad is Severidad.ERROR
    assert hallazgo.origen_ids == ("esp_ambientes:A", "esp_ambientes:B")


def test_en_la_frontera_de_0_0100_m2_la_hoja_no_trae_r15() -> None:
    a = ambiente("A", largo="1", ancho="1")
    b = ambiente("B", x0="0.99", largo="1", ancho="1")  # 0,0100 m2: pasa
    assert _r15(_elaborar(espacio([a, b]))) == []


def test_of001_limpio_no_trae_r15_en_la_hoja() -> None:
    assert _r15(_elaborar(espacio_of001())) == []
