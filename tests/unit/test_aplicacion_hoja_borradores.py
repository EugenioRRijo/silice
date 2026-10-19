"""El registro de borradores vivos de la hoja (T10, 3b-1; diseno §3.1, prueba 3b-B15).

El borrador vive en el servidor, en memoria, por ficha de sesion (D-2). Aqui se prueba el registro
sin FastAPI: ciclo de vida con reloj inyectado, topes por ficha y global, tope de bytes estimados,
aislamiento entre fichas, `rev` y el olvido/herencia que `api.caso_web` dispara.

Oraculos a mano: los numeros del diseno (4 por ficha, 64 en el proceso, 8 horas, 256 MiB) se
escriben aqui como literales; ninguno se lee del modulo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from aplicacion.hoja import Borrador
from aplicacion.hoja_borradores import (
    BorradorInexistente,
    RevDesactualizado,
    Registro,
)

MIB = 1024 * 1024
INICIO = datetime(2026, 10, 19, 9, 0, 0)


class Reloj:
    """Un reloj que solo avanza cuando la prueba lo dice."""

    def __init__(self) -> None:
        self.ahora = INICIO

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta) -> None:
        self.ahora += timedelta(**delta)


def _borrador(moneda: str = "USD") -> Borrador:
    return Borrador(fecha=date(2026, 10, 19), moneda=moneda)


def _crear(registro: Registro, huella: str = "ficha-a", proyecto: str = "P", version="001"):
    return registro.crear(huella, "caso-1", proyecto, version, _borrador(), None)


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def registro(reloj: Reloj) -> Registro:
    return Registro(reloj=reloj)


def test_un_borrador_nuevo_tiene_id_impredecible_rev_cero_y_es_de_su_ficha(registro):
    uno, otro = _crear(registro), _crear(registro, proyecto="Q")
    assert uno.id != otro.id
    for vivo in (uno, otro):
        assert len(vivo.id) >= 16 and vivo.id.replace("-", "").replace("_", "").isalnum()
    assert (uno.rev, uno.huella, uno.caso, uno.proyecto, uno.version) == (
        0,
        "ficha-a",
        "caso-1",
        "P",
        "001",
    )
    assert registro.obtener("ficha-a", uno.id) is uno


def test_un_borrador_de_otra_ficha_no_existe(registro):
    vivo = _crear(registro)
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-b", vivo.id)
    registro.descartar("ficha-b", vivo.id)  # ajeno: no lo borra y no avisa
    assert registro.obtener("ficha-a", vivo.id) is vivo


def test_descartar_es_idempotente_y_un_id_desconocido_no_falla(registro):
    vivo = _crear(registro)
    registro.descartar("ficha-a", vivo.id)
    registro.descartar("ficha-a", vivo.id)
    registro.descartar("ficha-a", "id-que-nunca-existio-0000")
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-a", vivo.id)


def test_pasadas_ocho_horas_sin_uso_el_borrador_vence(registro, reloj):
    vivo = _crear(registro)
    reloj.avanzar(hours=7, minutes=59)
    assert registro.obtener("ficha-a", vivo.id) is vivo  # tocarlo renueva el plazo
    reloj.avanzar(hours=7, minutes=59)
    assert registro.obtener("ficha-a", vivo.id) is vivo
    reloj.avanzar(hours=8)
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-a", vivo.id)


def test_crear_barre_los_vencidos_de_cualquier_ficha(registro, reloj):
    viejo = _crear(registro, "ficha-b")
    reloj.avanzar(hours=9)
    _crear(registro, "ficha-a")
    assert registro.listar("ficha-b") == []
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-b", viejo.id)


def test_el_quinto_borrador_de_una_ficha_descarta_el_primero(registro, reloj):
    vivos = []
    for i in range(5):
        reloj.avanzar(minutes=1)
        vivos.append(_crear(registro, proyecto=f"P{i}"))
    assert [v.id for v in registro.listar("ficha-a")] == [v.id for v in vivos[1:]]
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-a", vivos[0].id)


def test_el_descarte_por_tope_elige_al_menos_reciente_por_uso_no_por_creacion(registro, reloj):
    vivos = []
    for i in range(4):
        reloj.avanzar(minutes=1)
        vivos.append(_crear(registro, proyecto=f"P{i}"))
    reloj.avanzar(minutes=1)
    registro.obtener("ficha-a", vivos[0].id)  # el mas viejo se usa: ya no es el menos reciente
    reloj.avanzar(minutes=1)
    _crear(registro, proyecto="P4")
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-a", vivos[1].id)
    assert registro.obtener("ficha-a", vivos[0].id) is vivos[0]


def test_el_borrador_sesenta_y_cinco_del_proceso_descarta_el_mas_antiguo(registro, reloj):
    primero = None
    for ficha in range(16):  # 16 fichas x 4 = 64 borradores
        for i in range(4):
            reloj.avanzar(seconds=1)
            vivo = _crear(registro, f"ficha-{ficha}", f"P{i}")
            primero = primero or vivo
    assert sum(len(registro.listar(f"ficha-{n}")) for n in range(17)) == 64
    reloj.avanzar(seconds=1)
    _crear(registro, "ficha-nueva")
    assert sum(len(registro.listar(f"ficha-{n}")) for n in range(16)) == 63
    assert len(registro.listar("ficha-nueva")) == 1
    with pytest.raises(BorradorInexistente):
        registro.obtener("ficha-0", primero.id)


def test_si_el_total_estimado_supera_256_mib_se_expulsa_el_mas_antiguo(reloj):
    registro = Registro(reloj=reloj, medir=lambda _borrador: 100 * MIB)
    uno = _crear(registro, "ficha-a", "P1")
    reloj.avanzar(seconds=1)
    dos = _crear(registro, "ficha-b", "P2")
    reloj.avanzar(seconds=1)
    assert (uno.tamano, dos.tamano) == (100 * MIB, 100 * MIB)
    tres = _crear(registro, "ficha-c", "P3")  # 300 MiB > 256 MiB: se va el mas antiguo
    assert registro.listar("ficha-a") == []
    assert registro.listar("ficha-b") == [dos] and registro.listar("ficha-c") == [tres]


def test_un_borrador_mas_grande_que_el_tope_se_queda_solo_en_vez_de_expulsarse(reloj):
    registro = Registro(reloj=reloj, medir=lambda _borrador: 300 * MIB)
    uno = _crear(registro, "ficha-a")
    reloj.avanzar(seconds=1)
    otro = _crear(registro, "ficha-b")
    assert registro.listar("ficha-a") == [] and registro.listar("ficha-b") == [otro]
    assert uno.id != otro.id


def test_el_tamano_se_estima_con_pickle_del_borrador(registro):
    import pickle

    vivo = _crear(registro)
    assert vivo.tamano == len(pickle.dumps(vivo.borrador))
    assert 0 < vivo.tamano < MIB


def test_olvidar_borra_todos_los_de_la_ficha_y_solo_ellos(registro):
    _crear(registro, "ficha-a", "P1")
    _crear(registro, "ficha-a", "P2")
    ajeno = _crear(registro, "ficha-b")
    registro.olvidar("ficha-a")
    assert registro.listar("ficha-a") == []
    assert registro.listar("ficha-b") == [ajeno]
    registro.olvidar("ficha-que-no-existe")  # no falla


def test_heredar_pasa_los_borradores_a_la_ficha_nueva(registro):
    vivo = _crear(registro, "ficha-a")
    registro.heredar("ficha-a", "ficha-b")
    assert registro.listar("ficha-a") == []
    assert registro.obtener("ficha-b", vivo.id) is vivo
    assert vivo.huella == "ficha-b"  # su dueño ahora es la ficha nueva


def test_olvidar_todo_vacia_el_registro(registro):
    _crear(registro, "ficha-a")
    _crear(registro, "ficha-b")
    registro.olvidar_todo()
    assert registro.listar("ficha-a") == [] and registro.listar("ficha-b") == []


def test_reemplazar_sube_rev_invalida_la_cache_y_exige_el_rev_visto(registro):
    vivo = _crear(registro)
    vivo.calculo = (0, object(), [])  # lo que la vista deja en cache para ese rev
    nuevo = _borrador("Bs")
    devuelto = registro.reemplazar("ficha-a", vivo.id, nuevo, rev=0)
    assert devuelto is vivo and vivo.rev == 1 and vivo.borrador is nuevo
    assert vivo.calculo is None
    with pytest.raises(RevDesactualizado):
        registro.reemplazar("ficha-a", vivo.id, _borrador(), rev=0)  # ya es el 1
    assert vivo.rev == 1 and vivo.borrador is nuevo  # nada cambio


def test_reemplazar_un_borrador_ajeno_o_vencido_no_existe(registro, reloj):
    vivo = _crear(registro)
    with pytest.raises(BorradorInexistente):
        registro.reemplazar("ficha-b", vivo.id, _borrador(), rev=0)
    reloj.avanzar(hours=8)
    with pytest.raises(BorradorInexistente):
        registro.reemplazar("ficha-a", vivo.id, _borrador(), rev=0)


def test_listar_devuelve_los_de_mi_ficha_del_mas_reciente_al_mas_antiguo_por_uso(registro, reloj):
    uno = _crear(registro, proyecto="P1")
    reloj.avanzar(minutes=1)
    dos = _crear(registro, proyecto="P2")
    reloj.avanzar(minutes=1)
    registro.obtener("ficha-a", uno.id)
    assert [v.id for v in registro.listar("ficha-a")] == [uno.id, dos.id]


def test_el_modulo_ofrece_las_funciones_de_la_capa_sobre_un_registro_del_proceso():
    """Las que usan `api.caso_web` y las rutas: delegan en el registro unico del proceso."""
    from aplicacion import hoja_borradores as hb

    hb.olvidar_todo()
    vivo = hb.crear("ficha-x", "caso-1", "P", None, _borrador(), None)
    assert hb.obtener("ficha-x", vivo.id) is vivo
    assert hb.listar("ficha-x") == [vivo]
    hb.heredar("ficha-x", "ficha-y")
    assert hb.listar("ficha-x") == [] and hb.obtener("ficha-y", vivo.id) is vivo
    hb.descartar("ficha-y", vivo.id)
    hb.olvidar("ficha-y")
    hb.olvidar_todo()
    assert hb.listar("ficha-y") == []
