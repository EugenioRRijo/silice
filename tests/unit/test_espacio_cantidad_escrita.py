"""R8 marca la cantidad que el usuario escribe a mano en lugar de la calculada (DA-SF-5, SF3).

Spec §5.5 (DA-SF-5): una cantidad derivada se puede sobrescribir a mano, con fuente, y R8 la marca
como ADVERTENCIA. La marca cita el `origen_id` del item (que a su vez cita las filas `esp_*` de
donde sale la cantidad), de modo que la columna Estado de la hoja la lleva a esas filas. Sin
cantidades escritas R8 no cambia: las demas pruebas de R8 (`test_espacio_reglas.py`) lo vigilan.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from adapters.espacio import OrigenMedida, TipoOrigen
from adapters.espacio.reglas import CantidadEscrita, OrigenDeLaMedida, reglas_espacio
from core.contracts import Severidad
from core.contracts.presupuesto import Presupuesto
from tests.fixtures.espacio_bano import espacio_bano

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())


def _limpio():
    levantamiento = OrigenMedida(
        id="O1",
        tipo=TipoOrigen.LEVANTAMIENTO,
        referencia={"fecha": "2026-10-05", "responsable": "E"},
    )
    return replace(espacio_bano(), origenes=(levantamiento,))


def test_una_cantidad_escrita_da_una_advertencia_que_cita_el_origen_del_item():
    escrita = CantidadEscrita("AF-TUB-PVC-3/4", "esp_puntos:P1;esp_fuentes:F1", D("5"), D("12.5"))

    hallazgos = OrigenDeLaMedida(_limpio(), (escrita,)).evaluar(VACIO)

    assert len(hallazgos) == 1
    h = hallazgos[0]
    assert (h.regla, h.severidad) == ("R8", Severidad.ADVERTENCIA)
    assert h.origen_ids == ("esp_puntos:P1;esp_fuentes:F1",)
    assert "AF-TUB-PVC-3/4" in h.descripcion
    assert "a mano" in h.descripcion
    assert (h.valor_esperado, h.valor_observado) == (D("5"), D("12.5"))


def test_sin_cantidades_escritas_r8_no_cambia():
    espacio = _limpio()

    assert OrigenDeLaMedida(espacio, ()).evaluar(VACIO) == OrigenDeLaMedida(espacio).evaluar(VACIO)


def test_una_cantidad_escrita_igual_a_la_anterior_no_es_una_marca():
    igual = CantidadEscrita("AF-TUB-PVC-3/4", "esp_puntos:P1", D("5"), D("5.000"))

    assert OrigenDeLaMedida(_limpio(), (igual,)).evaluar(VACIO) == []


def test_reglas_espacio_pasa_las_cantidades_escritas_solo_a_r8():
    escrita = CantidadEscrita("X", "esp_puntos:P1", D("1"), D("2"))

    r8, r9, r10 = reglas_espacio(_limpio(), (escrita,))

    assert len(r8.evaluar(VACIO)) == 1
    assert r9.evaluar(VACIO) == []
    assert r10.evaluar(VACIO) == []


def test_un_item_sin_espacio_tambien_se_marca_con_su_propio_origen():
    """Una clinica sin hoja de metrajes: la cantidad escrita cita el origen del item."""
    escrita = CantidadEscrita("LB-01-EXC", "T-01", D("100"), D("90"))

    [h] = OrigenDeLaMedida(_limpio(), (escrita,)).evaluar(VACIO)

    assert h.origen_ids == ("T-01",)
    assert "fijada a mano" in h.descripcion
