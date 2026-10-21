"""El aviso `al_quitar` del registro de borradores (T10, 3e-2).

Contrato: `docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md`. La importacion de un plano vive
aparte del borrador, con su carpeta temporal (`aplicacion.hoja_plano`). Cuando un borrador sale del
registro, por CUALQUIER camino (descartar, vencer, expulsion por los topes por ficha, global o de
bytes, olvidar la ficha, olvidar todo), el registro avisa una vez a cada
funcion de `al_quitar` con el borrador que salio, para que nada quede en el disco. Heredar no quita
nada. El aviso ocurre FUERA del cerrojo del registro: quien recibe el aviso puede tomar su propio
cerrojo sin arriesgar un abrazo mortal con otro hilo que tenga ese cerrojo y espere al registro.

Oraculos a mano: los topes (4 por ficha, 64 globales, 256 MiB, 8 h) son los del diseno §3.1.
"""

from __future__ import annotations

import threading
from datetime import date, datetime, timedelta

import pytest

from aplicacion.hoja import Borrador
from aplicacion.hoja_borradores import BorradorInexistente, Registro

MIB = 1024 * 1024
INICIO = datetime(2026, 10, 20, 9, 0, 0)


class Reloj:
    def __init__(self) -> None:
        self.ahora = INICIO

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta) -> None:
        self.ahora += timedelta(**delta)


def _borrador() -> Borrador:
    return Borrador(fecha=date(2026, 10, 20))


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


def _con_aviso(registro: Registro) -> list[str]:
    avisados: list[str] = []
    registro.al_quitar.append(lambda vivo: avisados.append(vivo.id))
    return avisados


def _crear(registro: Registro, huella: str = "ficha-a", proyecto: str = "P"):
    return registro.crear(huella, "caso-1", proyecto, "001", _borrador(), None)


def test_descartar_avisa_una_vez_y_un_ajeno_o_desconocido_no_avisa(reloj):
    registro = Registro(reloj=reloj)
    avisados = _con_aviso(registro)
    vivo = _crear(registro)
    registro.descartar("ficha-b", vivo.id)  # ajeno: no se quita
    registro.descartar("ficha-a", "x" * 22)  # desconocido
    assert avisados == []
    registro.descartar("ficha-a", vivo.id)
    registro.descartar("ficha-a", vivo.id)  # idempotente: no avisa dos veces
    assert avisados == [vivo.id]


@pytest.mark.parametrize("como", ["obtener", "crear", "listar", "reemplazar"])
def test_vencer_avisa_en_cada_barrido(reloj, como):
    registro = Registro(reloj=reloj)
    avisados = _con_aviso(registro)
    viejo = _crear(registro, "ficha-b")
    reloj.avanzar(hours=8)
    if como == "obtener":
        with pytest.raises(BorradorInexistente):
            registro.obtener("ficha-b", viejo.id)
    elif como == "crear":
        _crear(registro, "ficha-a")
    elif como == "listar":
        assert registro.listar("ficha-a") == []
    else:
        with pytest.raises(BorradorInexistente):
            registro.reemplazar("ficha-b", viejo.id, _borrador(), rev=0)
    assert avisados == [viejo.id]


def test_el_quinto_de_una_ficha_avisa_del_que_expulsa(reloj):
    registro = Registro(reloj=reloj)
    avisados = _con_aviso(registro)
    vivos = []
    for i in range(5):
        reloj.avanzar(minutes=1)
        vivos.append(_crear(registro, proyecto=f"P{i}"))
    assert avisados == [vivos[0].id]


def test_el_sesenta_y_cinco_del_proceso_avisa_del_que_expulsa(reloj):
    registro = Registro(reloj=reloj)
    avisados = _con_aviso(registro)
    primero = None
    for ficha in range(16):
        for i in range(4):
            reloj.avanzar(seconds=1)
            vivo = _crear(registro, f"ficha-{ficha}", f"P{i}")
            primero = primero or vivo
    assert avisados == []
    reloj.avanzar(seconds=1)
    _crear(registro, "ficha-nueva")
    assert avisados == [primero.id]


def test_el_tope_de_bytes_avisa_al_crear_y_al_reestimar(reloj):
    medidas = {"valor": 100 * MIB}
    registro = Registro(reloj=reloj, medir=lambda _b: medidas["valor"], re_estimar_cada=1)
    avisados = _con_aviso(registro)
    uno = _crear(registro, "ficha-a", "P1")
    reloj.avanzar(seconds=1)
    dos = _crear(registro, "ficha-b", "P2")
    reloj.avanzar(seconds=1)
    tres = _crear(registro, "ficha-c", "P3")  # 300 MiB > 256 MiB: se va el mas antiguo
    assert avisados == [uno.id]
    medidas["valor"] = 200 * MIB  # al reestimar el tres crece y ya no caben dos y tres
    registro.reemplazar("ficha-c", tres.id, _borrador(), rev=0)
    assert avisados == [uno.id, dos.id]


def test_olvidar_y_olvidar_todo_avisan_de_cada_uno_y_heredar_no(reloj):
    registro = Registro(reloj=reloj)
    avisados = _con_aviso(registro)
    a1, a2 = _crear(registro, "ficha-a", "P1"), _crear(registro, "ficha-a", "P2")
    b = _crear(registro, "ficha-b")
    registro.heredar("ficha-b", "ficha-c")
    assert avisados == []
    registro.olvidar("ficha-a")
    assert sorted(avisados) == sorted([a1.id, a2.id])
    registro.olvidar_todo()
    assert sorted(avisados) == sorted([a1.id, a2.id, b.id])


def test_cada_funcion_registrada_recibe_el_aviso_aunque_otra_falle(reloj):
    registro = Registro(reloj=reloj)

    def falla(_vivo):
        raise RuntimeError("un aviso que falla")

    registro.al_quitar.append(falla)
    avisados = _con_aviso(registro)
    vivo = _crear(registro)
    registro.descartar("ficha-a", vivo.id)  # no lanza
    assert avisados == [vivo.id]
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-a", vivo.id)


@pytest.mark.parametrize("como", ["descartar", "obtener", "olvidar"])
def test_el_aviso_llega_fuera_del_cerrojo_del_registro(reloj, como):
    """Desde el aviso, OTRO hilo puede usar el registro: el cerrojo ya se solto."""
    registro = Registro(reloj=reloj)
    vivo = _crear(registro)
    terminados: list[bool] = []

    def aviso(_vivo):
        otro = threading.Thread(target=lambda: registro.listar("ficha-z"))
        otro.start()
        otro.join(timeout=5)
        terminados.append(not otro.is_alive())

    registro.al_quitar.append(aviso)
    if como == "descartar":
        registro.descartar("ficha-a", vivo.id)
    elif como == "obtener":
        reloj.avanzar(hours=9)
        with pytest.raises(BorradorInexistente):
            registro.obtener("ficha-a", vivo.id)
    else:
        registro.olvidar("ficha-a")
    assert terminados == [True]


def test_el_modulo_expone_la_lista_de_avisos_del_registro_del_proceso():
    from aplicacion import hoja_borradores as hb

    assert hb.al_quitar is hb.REGISTRO.al_quitar
