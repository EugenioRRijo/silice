"""El registro de borradores vivos al editar (T10, 3c-1; diseno §3.1).

* M5 de 3b-1: `Registro.reemplazar` vuelve a estimar el tamano del borrador cada 20 cambios
  aceptados y, si el total pasa el tope de bytes, expulsa el menos usado (nunca el que se edita).

Oraculos a mano: el 20 sale del diseno (§3.1: «cada 20 cambios»); las medidas son numeros que la
prueba inyecta, no la estimacion real.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from aplicacion import hoja_borradores
from aplicacion.hoja import Borrador
from aplicacion.hoja_borradores import BorradorInexistente, Registro, RevDesactualizado

INICIO = datetime(2026, 10, 20, 9, 0, 0)


class Reloj:
    """Un reloj que avanza un segundo en cada lectura: el orden de uso queda sin empates."""

    def __init__(self) -> None:
        self.ahora = INICIO

    def __call__(self) -> datetime:
        self.ahora += timedelta(seconds=1)
        return self.ahora


def _borrador(etiqueta: str = "A") -> Borrador:
    return Borrador(fecha=date(2026, 10, 20), moneda=etiqueta)


class Medidor:
    """`medir` inyectable: el tamano que la prueba fija por borrador; cuenta las llamadas."""

    def __init__(self, tamanos: dict[str, int]) -> None:
        self.tamanos = tamanos
        self.llamadas = 0

    def __call__(self, borrador: Borrador) -> int:
        self.llamadas += 1
        return self.tamanos[borrador.moneda]


def _editar(registro: Registro, vivo, n: int, moneda: str = "A"):
    """`n` reemplazos aceptados seguidos (cada uno cambia el borrador)."""
    for i in range(n):
        vivo = registro.reemplazar(
            vivo.huella, vivo.id, replace(vivo.borrador, fecha=date(2026, 1, 1 + i % 28)), vivo.rev
        )
    return vivo


def test_el_tamano_se_vuelve_a_estimar_cada_20_cambios_y_no_antes() -> None:
    medidor = Medidor({"A": 100})
    registro = Registro(Reloj(), medir=medidor)
    vivo = registro.crear("h", "caso", "P", "001", _borrador(), None)
    assert medidor.llamadas == 1 and vivo.tamano == 100  # al crear

    medidor.tamanos["A"] = 700
    vivo = _editar(registro, vivo, 19)
    assert vivo.rev == 19 and medidor.llamadas == 1 and vivo.tamano == 100  # aun no

    vivo = _editar(registro, vivo, 1)
    assert vivo.rev == 20 and medidor.llamadas == 2 and vivo.tamano == 700  # el cambio 20

    vivo = _editar(registro, vivo, 19)
    assert vivo.rev == 39 and medidor.llamadas == 2
    vivo = _editar(registro, vivo, 1)
    assert vivo.rev == 40 and medidor.llamadas == 3  # y el 40


def test_un_rev_desactualizado_no_cuenta_como_cambio_ni_mide() -> None:
    medidor = Medidor({"A": 100})
    registro = Registro(Reloj(), medir=medidor)
    vivo = registro.crear("h", "caso", "P", "001", _borrador(), None)
    with pytest.raises(RevDesactualizado):
        registro.reemplazar("h", vivo.id, _borrador(), 7)
    assert (vivo.rev, medidor.llamadas) == (0, 1)


def test_si_al_medir_de_nuevo_el_total_pasa_el_tope_se_expulsa_el_menos_usado() -> None:
    """Tope 1000 bytes: A (400) y B (400) caben; A crece a 700 en su cambio 20 → 1100 > 1000 →
    sale B, que es el menos usado (A se acaba de editar)."""
    medidor = Medidor({"A": 400, "B": 400})
    registro = Registro(Reloj(), medir=medidor, bytes_maximos=1000)
    a = registro.crear("h", "caso", "P", "001", _borrador("A"), None)
    b = registro.crear("h", "caso", "Q", "001", _borrador("B"), None)
    medidor.tamanos["A"] = 700
    a = _editar(registro, a, 20)
    with pytest.raises(BorradorInexistente):
        registro.obtener("h", b.id)
    assert registro.obtener("h", a.id) is a and a.tamano == 700


def test_un_borrador_solo_se_queda_por_grande_que_crezca() -> None:
    medidor = Medidor({"A": 400})
    registro = Registro(Reloj(), medir=medidor, bytes_maximos=1000)
    a = registro.crear("h", "caso", "P", "001", _borrador("A"), None)
    medidor.tamanos["A"] = 5000
    a = _editar(registro, a, 20)
    assert registro.obtener("h", a.id) is a and a.tamano == 5000


def test_no_expulsa_a_quien_se_edita_aunque_sea_el_mas_viejo() -> None:
    """A es el mas antiguo pero B es el que se edita: se va A, no B."""
    medidor = Medidor({"A": 600, "B": 300})
    registro = Registro(Reloj(), medir=medidor, bytes_maximos=1000)
    a = registro.crear("h", "caso", "P", "001", _borrador("A"), None)
    b = registro.crear("h", "caso", "Q", "001", _borrador("B"), None)
    medidor.tamanos["B"] = 900
    b = _editar(registro, b, 20)
    with pytest.raises(BorradorInexistente):
        registro.obtener("h", a.id)
    assert registro.obtener("h", b.id) is b


def test_la_frecuencia_por_omision_es_de_20_cambios() -> None:
    assert hoja_borradores.RE_ESTIMAR_CADA == 20
