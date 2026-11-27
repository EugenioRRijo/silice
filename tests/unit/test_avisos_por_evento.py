"""C11b: el servidor crea notificaciones cuando pasa algo (`aplicacion.avisos_por_evento`).

Especificación: `docs/especificaciones/2026-11-26-notificaciones-por-evento.md` (acordada con
Eugenio el 2026-11-26). Cuatro categorías:

1. `por_dictaminar`: una versión espera su dictamen, para quienes revisan (menos quien la envió), y
   un recordatorio desde los 2 días hábiles de espera (barrido al listar). No se apaga para quien
   revisa.
2. `dictamen`: su versión fue aprobada, aprobada con observaciones, devuelta (Advertencia) o
   retirada, para quien la envió (no si la cerró esa misma cuenta).
3. `compras`: un material sin pedir desde 2 días hábiles antes de «pedir a más tardar»
   (Advertencia) y desde ese día (Error, como la procura), para quien trabajó en la obra.
4. `listas_de_precios`: se cargó una lista o referencia nueva, para quienes arman (menos quien la
   cargó).

Datos construidos y ficticios (Ana, Rita, Rosa, Tomás, Vera; la «Vivienda Demo 80 m2» de las
fixtures). Oráculos escritos a mano: títulos, detalles, rutas, gravedades y fechas (las de compras
salen del encabezado de `tests/unit/test_procura.py`).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion import avisos_por_evento as avisos
from aplicacion import indice_aprobaciones
from aplicacion.avisos_por_evento import Categoria, Evento, PreferenciaInvalida
from aplicacion.entrega_de_obra import fijar_entrega
from aplicacion.indice_aprobaciones import FilaIndice, Reflejo
from aplicacion.procura import registrar_compra
from aplicacion.tablas_entrega import crear_esquema_entrega
from aplicacion.tablas_indice_aprobacion import METADATA_INDICE_APROBACION
from aplicacion.tablas_procura import crear_esquema_procura
from core.catalog import abrir_sesion as abrir_sesion_caso
from core.catalog import crear_motor as crear_motor_caso
from operacion.base_datos import preparar_base
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Base, Notificacion, Usuario
from seguridad.permisos import roles_de
from seguridad.sesiones import SesionActiva
from tests.fixtures import procura_vivienda as pv
from tests.fixtures.instalacion import administrador, persona

OBRA = "Vivienda Demo 80 m2"
ANA = "Ana <ana>"
RITA = "Rita <rita>"
ROSA = "Rosa <rosa>"
VIERNES = datetime(2026, 11, 20, 10, 0)
LUNES = datetime(2026, 11, 23, 9, 0)
MARTES = datetime(2026, 11, 24, 9, 0)
MIERCOLES = datetime(2026, 11, 25, 9, 0)
AHORA = datetime(2026, 11, 26, 10, 0)
RUTA_APROBACIONES = "/obra/vivienda.db/1/aprobaciones"


# --- la instalación con sus cuentas ---------------------------------------------------------------


@pytest.fixture
def bd(tmp_path: Path) -> Iterator[Session]:
    """`instalacion.db` con las tablas de seguridad y el índice de aprobaciones, y las cuentas:
    admin (administrador), ana y tomas (arma), rita (revisa), rosa (arma y revisa) y vera (revisa,
    desactivada)."""
    motor = crear_motor(tmp_path / "instalacion.db")
    Base.metadata.create_all(motor)
    METADATA_INDICE_APROBACION.create_all(motor)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, tmp_path)
        persona(sesion, admin, "ana", ("arma",))
        persona(sesion, admin, "tomas", ("arma",))
        persona(sesion, admin, "rita", ("revisa",))
        persona(sesion, admin, "rosa", ("arma", "revisa"))
        vera = persona(sesion, admin, "vera", ("revisa",))
        vera.activo = False
        sesion.commit()
        yield sesion
    finally:
        sesion.close()
        motor.dispose()


def _usuario(sesion: Session, login: str) -> Usuario:
    return sesion.scalars(select(Usuario).where(Usuario.login == login)).one()


def _cuenta(sesion: Session, login: str) -> SesionActiva:
    usuario = _usuario(sesion, login)
    return SesionActiva(
        huella_ficha="ficha-de-prueba",
        usuario_id=usuario.id,
        login=usuario.login,
        nombre=usuario.nombre,
        roles=roles_de(usuario.roles),
        debe_cambiar_clave=False,
        restablecida_por_admin=False,
    )


def _de(sesion: Session, login: str) -> list[Notificacion]:
    """Las notificaciones de `login`, en el orden en que se crearon."""
    return list(
        sesion.scalars(
            select(Notificacion)
            .where(Notificacion.usuario_id == _usuario(sesion, login).id)
            .order_by(Notificacion.id)
        )
    )


def _forma(n: Notificacion) -> tuple[str, str, str, str, str]:
    return (n.gravedad, n.titulo, n.detalle, n.enlace_texto, n.enlace_ruta)


def _fila(envio_id: int = 1, **campos) -> FilaIndice:
    base = {
        "caso": "vivienda.db",
        "envio_id": envio_id,
        "proyecto": "1",
        "obra": OBRA,
        "version": "VIV-001",
        "total": Decimal("100"),
        "moneda": "Bs",
        "estado": "en_aprobacion",
        "enviado_por": ANA,
        "enviado_el": VIERNES,
        "dictamen_por": None,
        "dictamen_el": None,
        "nota": "",
        "notas": "",
        "armo": False,
    }
    return FilaIndice(**{**base, **campos})


def _aprobaciones(sesion: Session, antes, despues, ahora: datetime = AHORA, empresa=None) -> None:
    avisos.de_aprobaciones(sesion, antes, despues, ahora, carpeta_empresa=empresa)
    sesion.commit()


# --- categorías y preferencias ------------------------------------------------------------------


def test_las_cuatro_categorias_vienen_encendidas_y_cada_una_aplica_a_su_rol(bd: Session) -> None:
    ana = avisos.preferencias(bd, _usuario(bd, "ana").id)
    assert [(p.categoria, p.activa, p.aplica, p.obligatoria) for p in ana] == [
        ("por_dictaminar", True, False, False),
        ("dictamen", True, True, False),
        ("compras", True, True, False),
        ("listas_de_precios", True, True, False),
        ("entregas", True, True, False),
    ]
    rita = avisos.preferencias(bd, _usuario(bd, "rita").id)
    assert [(p.categoria, p.activa, p.aplica, p.obligatoria) for p in rita] == [
        ("por_dictaminar", True, True, True),
        ("dictamen", True, False, False),
        ("compras", True, False, False),
        ("listas_de_precios", True, False, False),
        ("entregas", True, False, False),
    ]
    assert [p.titulo for p in ana] == [
        "Versiones por dictaminar",
        "Dictamen de sus versiones",
        "Compras por pedir",
        "Listas de precios nuevas",
        "Entregas al cliente",
    ]
    assert [p.descripcion for p in ana] == [
        "Una versión espera su dictamen, y un recordatorio si lleva 2 días hábiles esperando.",
        "Una versión que usted envió fue aprobada, devuelta o retirada.",
        "Un material de una obra en la que trabajó debe pedirse pronto o ya debía pedirse.",
        "Se cargó una lista o una referencia de precios nueva.",
        "Se acerca o ya llegó la fecha de entrega al cliente de una obra en la que trabajó.",
    ]


def test_apagar_una_categoria_es_solo_de_esa_cuenta_y_se_puede_encender(bd: Session) -> None:
    ana, tomas = _usuario(bd, "ana").id, _usuario(bd, "tomas").id
    nuevas = avisos.fijar_preferencias(bd, ana, [("compras", False)])
    bd.commit()
    assert {p.categoria: p.activa for p in nuevas}["compras"] is False
    assert {p.categoria: p.activa for p in avisos.preferencias(bd, ana)} == {
        "por_dictaminar": True,
        "dictamen": True,
        "compras": False,
        "listas_de_precios": True,
        "entregas": True,
    }
    assert all(p.activa for p in avisos.preferencias(bd, tomas))
    avisos.fijar_preferencias(bd, ana, [("compras", True)])
    bd.commit()
    assert all(p.activa for p in avisos.preferencias(bd, ana))


def test_quien_revisa_no_puede_apagar_las_versiones_por_dictaminar(bd: Session) -> None:
    rita, rosa, ana = (_usuario(bd, login).id for login in ("rita", "rosa", "ana"))
    for quien in (rita, rosa):
        with pytest.raises(PreferenciaInvalida) as error:
            avisos.fijar_preferencias(bd, quien, [("por_dictaminar", False)])
        assert str(error.value) == (
            "Quien revisa recibe siempre las versiones que esperan su dictamen: esa categoría no "
            "se puede apagar."
        )
    # A quien no revisa no le aplica: apagarla no cambia nada, pero no es un error.
    avisos.fijar_preferencias(bd, ana, [("por_dictaminar", False)])
    assert {p.categoria: p.activa for p in avisos.preferencias(bd, ana)}["por_dictaminar"] is False


def test_una_categoria_desconocida_o_repetida_se_rechaza(bd: Session) -> None:
    ana = _usuario(bd, "ana").id
    with pytest.raises(PreferenciaInvalida, match="No existe la categoría «inexistente»."):
        avisos.fijar_preferencias(bd, ana, [("inexistente", False)])
    with pytest.raises(PreferenciaInvalida, match="La categoría «compras» está repetida."):
        avisos.fijar_preferencias(bd, ana, [("compras", False), ("compras", True)])
    assert all(p.activa for p in avisos.preferencias(bd, ana))


# --- emitir -------------------------------------------------------------------------------------


def _evento(clave: str = "prueba:1") -> Evento:
    return Evento(clave=clave, gravedad="info", titulo="Algo pasó", detalle="Detalle")


def test_emitir_crea_una_sola_vez_por_clave_y_persona(bd: Session) -> None:
    ana, tomas = _usuario(bd, "ana").id, _usuario(bd, "tomas").id
    assert avisos.emitir(bd, Categoria.COMPRAS, _evento(), [ana, tomas], AHORA) == [ana, tomas]
    assert avisos.emitir(bd, Categoria.COMPRAS, _evento(), [ana, tomas], AHORA) == []
    assert avisos.emitir(bd, Categoria.COMPRAS, _evento("prueba:2"), [ana], AHORA) == [ana]
    bd.commit()
    assert [n.clave_evento for n in _de(bd, "ana")] == ["prueba:1", "prueba:2"]
    assert [n.clave_evento for n in _de(bd, "tomas")] == ["prueba:1"]


def test_la_misma_clave_choca_en_la_base_para_la_misma_persona(bd: Session) -> None:
    """La clave única la guarda la base (no solo la consulta previa): dos inserciones iguales
    chocan y `emitir` lo absorbe sin deshacer lo demás."""
    from aplicacion import notificaciones
    from aplicacion.notificaciones import DatosNotificacion

    ana = _usuario(bd, "ana").id
    notificaciones.agregar(
        bd, ana, DatosNotificacion("info", "Primera"), AHORA, clave_evento="carrera:1"
    )
    bd.commit()
    with pytest.raises(Exception, match="UNIQUE"):
        with bd.begin_nested():
            notificaciones.agregar(
                bd, ana, DatosNotificacion("info", "Segunda"), AHORA, clave_evento="carrera:1"
            )
    assert [n.titulo for n in _de(bd, "ana")] == ["Primera"]


def test_la_categoria_apagada_no_crea_y_al_encenderla_vuelve_a_crear(bd: Session) -> None:
    ana = _usuario(bd, "ana").id
    avisos.fijar_preferencias(bd, ana, [("compras", False)])
    assert avisos.emitir(bd, Categoria.COMPRAS, _evento(), [ana], AHORA) == []
    assert avisos.emitir(bd, Categoria.LISTAS_DE_PRECIOS, _evento("l:1"), [ana], AHORA) == [ana]
    avisos.fijar_preferencias(bd, ana, [("compras", True)])
    assert avisos.emitir(bd, Categoria.COMPRAS, _evento(), [ana], AHORA) == [ana]


def test_la_categoria_1_llega_a_quien_revisa_aunque_la_haya_apagado_antes(bd: Session) -> None:
    """Rita apagó la categoría cuando aún no revisaba (fila guardada a mano): con `revisa`, manda
    la regla, no la fila."""
    from seguridad.modelo import PreferenciaNotificacion

    rita = _usuario(bd, "rita").id
    bd.add(PreferenciaNotificacion(usuario_id=rita, categoria="por_dictaminar", activa=False))
    bd.flush()
    assert avisos.emitir(bd, Categoria.POR_DICTAMINAR, _evento(), [rita], AHORA) == [rita]


# --- categoría 1 y 2: aprobaciones ----------------------------------------------------------------


def test_un_envio_nuevo_llega_a_quienes_revisan_menos_quien_lo_envio(bd: Session) -> None:
    _aprobaciones(bd, [], [_fila(nota="Primera entrega")])
    esperada = (
        "info",
        "VIV-001 de «Vivienda Demo 80 m2» espera su dictamen",
        "La envió Ana el 20/11/2026. Nota: Primera entrega",
        "Ver la aprobación",
        RUTA_APROBACIONES,
    )
    assert [_forma(n) for n in _de(bd, "rita")] == [esperada]
    assert [_forma(n) for n in _de(bd, "rosa")] == [esperada]
    for login in ("ana", "tomas", "vera", "admin"):
        assert _de(bd, login) == [], login
    assert _de(bd, "rita")[0].clave_evento == "aprobacion:vivienda.db:1:VIV-001:enviada"

    # Rosa (arma y revisa) envía la suya: le llega a Rita, no a ella misma.
    _aprobaciones(bd, [], [_fila(2, version="VIV-002", enviado_por=ROSA)])
    assert [n.titulo for n in _de(bd, "rosa")] == [esperada[1]]
    assert _de(bd, "rita")[-1].detalle == "La envió Rosa el 20/11/2026."


def test_la_carpeta_de_la_empresa_se_enlaza_como_empresa(bd: Session) -> None:
    _aprobaciones(bd, [], [_fila()], empresa="vivienda.db")
    assert _de(bd, "rita")[0].enlace_ruta == "/obra/empresa/1/aprobaciones"


def test_reflejar_lo_mismo_otra_vez_no_repite(bd: Session) -> None:
    fila = _fila()
    _aprobaciones(bd, [], [fila])
    _aprobaciones(bd, [], [fila])  # el reflejo se repuso: la clave ya está
    _aprobaciones(bd, [fila], [fila])  # sin cambios
    assert len(_de(bd, "rita")) == 1


def test_el_dictamen_llega_a_quien_envio(bd: Session) -> None:
    pendiente = _fila()
    devuelta = _fila(
        estado="devuelta",
        dictamen_por=RITA,
        dictamen_el=AHORA,
        notas="Falta el acero de la losa.",
    )
    _aprobaciones(bd, [pendiente], [devuelta])
    assert [_forma(n) for n in _de(bd, "ana")] == [
        (
            "advertencia",
            "Su versión VIV-001 de «Vivienda Demo 80 m2» fue devuelta",
            "Rita la devolvió el 26/11/2026. Notas: Falta el acero de la losa.",
            "Ver la aprobación",
            RUTA_APROBACIONES,
        )
    ]
    assert _de(bd, "ana")[0].clave_evento == "aprobacion:vivienda.db:1:VIV-001:devuelta"
    assert _de(bd, "rita") == []  # el envío ya estaba en el índice: nada nuevo por dictaminar
    _aprobaciones(bd, [pendiente], [devuelta])
    assert len(_de(bd, "ana")) == 1


@pytest.mark.parametrize(
    ("estado", "gravedad", "titulo", "detalle"),
    [
        (
            "aprobada",
            "info",
            "Su versión VIV-001 de «Vivienda Demo 80 m2» fue aprobada",
            "Rita la aprobó el 26/11/2026.",
        ),
        (
            "aprobada_con_observaciones",
            "info",
            "Su versión VIV-001 de «Vivienda Demo 80 m2» fue aprobada con observaciones",
            "Rita la aprobó con observaciones el 26/11/2026. Notas: Revise el friso.",
        ),
    ],
)
def test_aprobada_y_con_observaciones(
    bd: Session, estado: str, gravedad: str, titulo: str, detalle: str
) -> None:
    notas = "Revise el friso." if estado == "aprobada_con_observaciones" else ""
    cerrada = _fila(estado=estado, dictamen_por=RITA, dictamen_el=AHORA, notas=notas)
    _aprobaciones(bd, [_fila()], [cerrada])
    assert [(n.gravedad, n.titulo, n.detalle) for n in _de(bd, "ana")] == [
        (gravedad, titulo, detalle)
    ]


def test_quien_dictamina_su_propio_envio_no_se_avisa(bd: Session) -> None:
    propia = _fila(enviado_por=ROSA, estado="aprobada", dictamen_por=ROSA, dictamen_el=AHORA)
    _aprobaciones(bd, [_fila(enviado_por=ROSA)], [propia])
    assert _de(bd, "rosa") == []


def test_la_retirada_por_otra_cuenta_avisa_y_la_propia_no(bd: Session) -> None:
    retirada = _fila(estado="retirada")
    nueva = _fila(2, version="VIV-002", enviado_por=ROSA, enviado_el=AHORA)
    _aprobaciones(bd, [_fila()], [retirada, nueva])
    assert [_forma(n) for n in _de(bd, "ana")] == [
        (
            "info",
            "Su versión VIV-001 de «Vivienda Demo 80 m2» fue retirada",
            "Rosa envió VIV-002 el 26/11/2026 y retiró la suya.",
            "Ver la aprobación",
            RUTA_APROBACIONES,
        )
    ]
    # Ana retira la suya al enviar otra: no se avisa a sí misma.
    _aprobaciones(
        bd,
        [_fila(3, version="VIV-003")],
        [
            _fila(3, version="VIV-003", estado="retirada"),
            _fila(4, version="VIV-004", enviado_el=AHORA),
        ],
    )
    assert len(_de(bd, "ana")) == 1


def test_un_dictamen_de_hace_mas_de_30_dias_no_se_avisa_al_reponer(bd: Session) -> None:
    """El índice de una carpeta que nunca se reflejó trae su historia: lo de hace más de 30 días ya
    no es noticia (la retención de la campanita). Lo que aún espera dictamen sí."""
    vieja = _fila(estado="aprobada", dictamen_por=RITA, dictamen_el=datetime(2026, 10, 26, 9, 59))
    justa = _fila(2, estado="aprobada", dictamen_por=RITA, dictamen_el=datetime(2026, 10, 27, 10))
    pendiente = _fila(3, version="VIV-003", enviado_el=datetime(2026, 9, 1, 9))
    _aprobaciones(bd, [], [vieja, justa, pendiente])
    assert [n.clave_evento for n in _de(bd, "ana")] == ["aprobacion:vivienda.db:2:VIV-001:aprobada"]
    assert [n.clave_evento for n in _de(bd, "rita")] == ["aprobacion:vivienda.db:3:VIV-003:enviada"]


def test_el_dictamen_apagado_no_llega(bd: Session) -> None:
    avisos.fijar_preferencias(bd, _usuario(bd, "ana").id, [("dictamen", False)])
    _aprobaciones(bd, [_fila()], [_fila(estado="devuelta", dictamen_por=RITA, dictamen_el=AHORA)])
    assert _de(bd, "ana") == []


def test_escribir_el_reflejo_pasa_lo_de_antes_y_lo_de_despues(bd: Session) -> None:
    vistos: list[tuple[tuple[FilaIndice, ...], tuple[FilaIndice, ...]]] = []

    def anotar(antes, despues) -> None:
        vistos.append((tuple(antes), tuple(despues)))

    primero = Reflejo("vivienda.db", (_fila(),))
    assert indice_aprobaciones.escribir_reflejo(bd, primero, al_reflejar=anotar)
    cerrado = Reflejo(
        "vivienda.db", (_fila(estado="devuelta", dictamen_por=RITA, dictamen_el=AHORA),)
    )
    assert indice_aprobaciones.escribir_reflejo(bd, cerrado, al_reflejar=anotar)
    # Un reflejo viejo que llega tarde no se escribe ni avisa.
    assert not indice_aprobaciones.escribir_reflejo(bd, primero, al_reflejar=anotar)
    assert vistos == [((), primero.filas), (primero.filas, cerrado.filas)]


def test_un_fallo_al_avisar_no_desdice_el_indice(bd: Session, monkeypatch) -> None:
    def falla(*_a, **_k):
        raise RuntimeError("sin avisos")

    monkeypatch.setattr(avisos, "emitir", falla)
    _aprobaciones(bd, [], [_fila()])  # no lanza
    assert _de(bd, "rita") == []


# --- categoría 1: el recordatorio al listar ------------------------------------------------------


def _indice(bd: Session, *filas: FilaIndice) -> None:
    indice_aprobaciones.escribir_reflejo(bd, Reflejo("vivienda.db", filas), forzar=True)
    bd.commit()


def _barrer(bd: Session, login: str, ahora: datetime, abrir_carpeta=None, caso="vivienda.db"):
    avisos.barrer(
        bd,
        _cuenta(bd, login),
        ahora,
        carpeta_empresa=None,
        caso=caso,
        abrir_carpeta=abrir_carpeta,
    )
    bd.commit()


def test_el_recordatorio_nace_a_los_2_dias_habiles_y_una_sola_vez(bd: Session) -> None:
    _indice(bd, _fila())  # enviada el viernes 20/11 a las 10:00
    _barrer(bd, "rita", LUNES)  # 1 día hábil
    assert _de(bd, "rita") == []
    _barrer(bd, "rita", MARTES)  # 2 días hábiles
    assert [_forma(n) for n in _de(bd, "rita")] == [
        (
            "advertencia",
            "VIV-001 de «Vivienda Demo 80 m2» sigue esperando su dictamen",
            "Se envió el 20/11/2026 y lleva 2 días hábiles sin dictamen.",
            "Ver la aprobación",
            RUTA_APROBACIONES,
        )
    ]
    assert _de(bd, "rita")[0].clave_evento == "aprobacion:vivienda.db:1:VIV-001:recordatorio"
    _barrer(bd, "rita", MIERCOLES)
    assert len(_de(bd, "rita")) == 1


def test_el_recordatorio_es_solo_para_quien_lista_y_revisa(bd: Session) -> None:
    _indice(bd, _fila(), _fila(2, version="VIV-002", enviado_por=ROSA))
    _barrer(bd, "ana", MARTES)  # arma: no revisa
    _barrer(bd, "rosa", MARTES)  # revisa: la suya (VIV-002) no; la de Ana sí
    assert _de(bd, "ana") == [] and _de(bd, "rita") == []
    assert [n.clave_evento for n in _de(bd, "rosa")] == [
        "aprobacion:vivienda.db:1:VIV-001:recordatorio"
    ]


def test_lo_que_ya_tiene_dictamen_no_se_recuerda(bd: Session) -> None:
    _indice(bd, _fila(estado="aprobada", dictamen_por=RITA, dictamen_el=LUNES))
    _barrer(bd, "rita", MIERCOLES)
    assert _de(bd, "rita") == []


# --- categoría 3: compras por pedir ---------------------------------------------------------------

#: Los materiales de la vivienda que la prueba da por pedidos para dejar solo el mortero
#: (pedir a más tardar el vie 04/12/2026; sin feriados) y la pintura (el 07/01/2027).
PEDIDOS = (
    ("Agua", "m3"),
    ("Cemento gris", "saco"),
    ("Arena lavada", "m3"),
    ("Cabilla de 1/2 pulgada", "kg"),
    ("Bloque de arcilla de 15 cm", "pieza"),
)
MORTERO_AVISO = (
    "advertencia",
    "Pida Mortero premezclado antes del 04/12/2026.",
    "Obra «Vivienda Demo 80 m2». Anote el pedido en la procura cuando lo haga.",
    "Ver la procura",
    "/obra/carpeta.db/1/control",
)
MORTERO_VENCIDO = (
    "error",
    "Mortero premezclado no está pedido y debía pedirse el 04/12/2026.",
    "Obra «Vivienda Demo 80 m2». Anote el pedido en la procura cuando lo haga.",
    "Ver la procura",
    "/obra/carpeta.db/1/control",
)


@pytest.fixture
def carpeta(tmp_path: Path) -> Iterator:
    ruta = tmp_path / "carpeta.db"
    preparar_base(ruta)
    motor = crear_motor_caso(f"sqlite:///{ruta.as_posix()}")
    crear_esquema_procura(motor)
    try:
        yield motor
    finally:
        motor.dispose()


def _vivienda(motor, *, feriados: tuple[date, ...] = (), linea_base: bool = True) -> None:
    with abrir_sesion_caso(motor) as s:
        pv.sembrar(s)
        if linea_base:
            pv.declarar_linea_base(s, feriados)
        for descripcion, unidad in PEDIDOS:
            registrar_compra(
                s,
                OBRA,
                descripcion=descripcion,
                unidad=unidad,
                evento="pedida",
                fecha=date(2026, 10, 27),
                responsable=ANA,
                ahora=datetime(2026, 10, 27, 17),
            )
        s.commit()


def _abridor(motor, abiertas: list[int] | None = None):
    @contextmanager
    def abrir():
        if abiertas is not None:
            abiertas.append(1)
        with abrir_sesion_caso(motor) as s:
            yield s

    return abrir


def _compras(bd: Session, motor, login: str, dia: date, abiertas=None) -> None:
    _barrer(
        bd,
        login,
        datetime(dia.year, dia.month, dia.day, 8),
        _abridor(motor, abiertas),
        "carpeta.db",
    )


def test_compras_bordes_de_fecha_aviso_vencida_y_sin_repetir(bd: Session, carpeta) -> None:
    _vivienda(carpeta)
    _compras(bd, carpeta, "ana", date(2026, 12, 1))  # mar: 3 días hábiles antes
    assert _de(bd, "ana") == []
    _compras(bd, carpeta, "ana", date(2026, 12, 2))  # mié: 2 días hábiles antes
    assert [_forma(n) for n in _de(bd, "ana")] == [MORTERO_AVISO]
    _compras(bd, carpeta, "ana", date(2026, 12, 3))  # jue: 1 día hábil antes
    assert [_forma(n) for n in _de(bd, "ana")] == [MORTERO_AVISO]
    _compras(bd, carpeta, "ana", date(2026, 12, 4))  # vie: el día
    assert [_forma(n) for n in _de(bd, "ana")] == [MORTERO_AVISO, MORTERO_VENCIDO]
    _compras(bd, carpeta, "ana", date(2026, 12, 7))  # lun: ya vencida
    assert [_forma(n) for n in _de(bd, "ana")] == [MORTERO_AVISO, MORTERO_VENCIDO]
    claves = [n.clave_evento for n in _de(bd, "ana")]
    assert [c.rsplit(":", 2)[1:] for c in claves] == [
        ["2026-12-04", "aviso"],
        ["2026-12-04", "vencida"],
    ]
    assert all(c.startswith("compra:carpeta.db:1:") for c in claves)


def test_compras_solo_para_quien_trabajo_en_la_obra(bd: Session, carpeta) -> None:
    _vivienda(carpeta)
    _compras(bd, carpeta, "tomas", date(2026, 12, 4))  # arma, pero no guardó ni envió nada
    _compras(bd, carpeta, "rita", date(2026, 12, 4))  # revisa
    assert _de(bd, "tomas") == [] and _de(bd, "rita") == []


def test_compras_con_un_feriado_de_la_linea_base(bd: Session, carpeta) -> None:
    """Feriado el mié 02/12: el mortero se necesita el jue 10/12, se pide a más tardar el lun
    07/12 y se avisa desde el jue 03/12 (vie 04 es 1, jue 03 es 2)."""
    _vivienda(carpeta, feriados=(date(2026, 12, 2),))
    _compras(bd, carpeta, "ana", date(2026, 12, 2))
    assert _de(bd, "ana") == []
    _compras(bd, carpeta, "ana", date(2026, 12, 3))
    assert [n.titulo for n in _de(bd, "ana")] == ["Pida Mortero premezclado antes del 07/12/2026."]


def test_sin_linea_base_no_hay_avisos_de_compra(bd: Session, carpeta) -> None:
    _vivienda(carpeta, linea_base=False)
    _compras(bd, carpeta, "ana", date(2027, 2, 1))
    assert _de(bd, "ana") == []


def test_compras_apagadas_no_abren_la_carpeta(bd: Session, carpeta) -> None:
    _vivienda(carpeta)
    avisos.fijar_preferencias(
        bd, _usuario(bd, "ana").id, [("compras", False), ("entregas", False)]
    )
    abiertas: list[int] = []
    _compras(bd, carpeta, "ana", date(2026, 12, 4), abiertas)
    assert _de(bd, "ana") == [] and abiertas == []


# --- categoría 5: entregas al cliente (Lote G5) ---------------------------------------------------

ENTREGA_AVISO = (
    "advertencia",
    "Entregue «Vivienda Demo 80 m2» antes del 04/12/2026.",
    "Obra «Vivienda Demo 80 m2». La fecha de entrega al cliente es el 04/12/2026.",
    "Ver el resumen de la obra",
    "/obra/carpeta.db/1/resumen",
)
#: El mismo día de la entrega (auditoría antes de medicion-v1, #7): sigue siendo Error (spec §2),
#: pero no dice «debía entregarse» de hoy.
ENTREGA_HOY = (
    "error",
    "Hoy vence la entrega de «Vivienda Demo 80 m2».",
    "Obra «Vivienda Demo 80 m2». La fecha de entrega al cliente es hoy, 04/12/2026.",
    "Ver el resumen de la obra",
    "/obra/carpeta.db/1/resumen",
)
ENTREGA_VENCIDA = (
    "error",
    "«Vivienda Demo 80 m2» no está entregada y debía entregarse el 04/12/2026.",
    "Obra «Vivienda Demo 80 m2». La fecha de entrega al cliente era el 04/12/2026.",
    "Ver el resumen de la obra",
    "/obra/carpeta.db/1/resumen",
)


def _vivienda_con_entrega(
    motor,
    fecha_entrega: date = date(2026, 12, 4),
    *,
    feriados: tuple[date, ...] = (),
    linea_base: bool = False,
) -> None:
    crear_esquema_entrega(motor)
    with abrir_sesion_caso(motor) as s:
        pv.sembrar(s)
        if linea_base:
            pv.declarar_linea_base(s, feriados)
        fijar_entrega(
            s,
            OBRA,
            fecha_entrega,
            responsable=ANA,
            ahora=datetime(2026, 11, 1, 9, 0),
        )
        s.commit()


def test_entregas_bordes_de_fecha_aviso_vencida_y_sin_repetir(bd: Session, carpeta) -> None:
    _vivienda_con_entrega(carpeta, date(2026, 12, 4))
    avisos.fijar_preferencias(bd, _usuario(bd, "ana").id, [("compras", False)])
    _compras(bd, carpeta, "ana", date(2026, 11, 30))  # lun: 4 días hábiles antes -> nada
    assert _de(bd, "ana") == []
    _compras(bd, carpeta, "ana", date(2026, 12, 1))  # mar: 3 días hábiles antes -> advertencia
    assert [_forma(n) for n in _de(bd, "ana")] == [ENTREGA_AVISO]
    _compras(bd, carpeta, "ana", date(2026, 12, 2))  # mié: 2 días hábiles antes -> no repite
    assert [_forma(n) for n in _de(bd, "ana")] == [ENTREGA_AVISO]
    _compras(bd, carpeta, "ana", date(2026, 12, 3))  # jue: 1 día hábil antes -> no repite
    assert [_forma(n) for n in _de(bd, "ana")] == [ENTREGA_AVISO]
    _compras(bd, carpeta, "ana", date(2026, 12, 4))  # vie: el día -> error «Hoy vence»
    assert [_forma(n) for n in _de(bd, "ana")] == [ENTREGA_AVISO, ENTREGA_HOY]
    _compras(bd, carpeta, "ana", date(2026, 12, 7))  # lun: después sin entregar -> no repite
    assert [_forma(n) for n in _de(bd, "ana")] == [ENTREGA_AVISO, ENTREGA_HOY]
    assert [n.clave_evento for n in _de(bd, "ana")] == [
        "entrega:carpeta.db:1:2026-12-04:aviso",
        "entrega:carpeta.db:1:2026-12-04:vencida",
    ]


def test_desde_el_dia_siguiente_dice_que_debia_entregarse(bd: Session, carpeta) -> None:
    """Quien lista por primera vez el lunes siguiente recibe la frase de vencida, no «Hoy vence»."""
    _vivienda_con_entrega(carpeta, date(2026, 12, 4))
    avisos.fijar_preferencias(bd, _usuario(bd, "ana").id, [("compras", False)])
    _compras(bd, carpeta, "ana", date(2026, 12, 5))  # sáb: el día siguiente
    assert [_forma(n) for n in _de(bd, "ana")] == [ENTREGA_VENCIDA]
    assert [n.clave_evento for n in _de(bd, "ana")] == ["entrega:carpeta.db:1:2026-12-04:vencida"]


def _exportar(bd: Session, motor, cuando: datetime) -> None:
    from core.models.cadena import EslabonVersion
    from seguridad.modelo import EventoAcceso

    with abrir_sesion_caso(motor) as s:
        sello = s.scalar(select(EslabonVersion.huella_eslabon))
    assert sello is not None
    bd.add(
        EventoAcceso(
            tipo="paquete exportado",
            fecha_hora=cuando,
            login_intentado="ana",
            ip_cliente="127.0.0.1",
            detalle=f"paq-1; version VIV-001; sello_version {sello}",
        )
    )
    bd.commit()


@pytest.mark.parametrize(
    ("exportado", "avisa"),
    [
        # La fecha se fijó el 01/11/2026 a las 09:00 (`_vivienda_con_entrega`).
        (datetime(2026, 10, 31, 17, 0), True),  # antes de fijar la fecha: no es esta entrega
        (datetime(2026, 11, 1, 8, 59), True),
        (datetime(2026, 11, 1, 9, 0), False),  # el mismo instante ya cuenta
        (datetime(2026, 11, 20, 10, 0), False),
    ],
)
def test_solo_cuenta_lo_exportado_desde_que_se_fijo_la_fecha(
    bd: Session, carpeta, exportado: datetime, avisa: bool
) -> None:
    """Auditoría antes de medicion-v1 (#9): un paquete exportado antes de fijar la fecha de entrega
    no es la entrega de esa fecha."""
    _vivienda_con_entrega(carpeta, date(2026, 12, 4))
    avisos.fijar_preferencias(bd, _usuario(bd, "ana").id, [("compras", False)])
    _exportar(bd, carpeta, exportado)
    _compras(bd, carpeta, "ana", date(2026, 12, 4))
    assert [_forma(n) for n in _de(bd, "ana")] == ([ENTREGA_HOY] if avisa else [])


def test_entregas_solo_para_quien_trabajo_en_la_obra_y_si_esta_encendida(
    bd: Session, carpeta
) -> None:
    _vivienda_con_entrega(carpeta, date(2026, 12, 4))
    _compras(bd, carpeta, "tomas", date(2026, 12, 4))  # arma, pero no trabajó en la obra
    _compras(bd, carpeta, "rita", date(2026, 12, 4))  # revisa
    assert _de(bd, "tomas") == [] and _de(bd, "rita") == []

    # Si Ana apaga «entregas», no se crea aviso de entrega.
    avisos.fijar_preferencias(
        bd, _usuario(bd, "ana").id, [("compras", False), ("entregas", False)]
    )
    _compras(bd, carpeta, "ana", date(2026, 12, 4))
    assert _de(bd, "ana") == []


def test_entregas_con_feriado_y_obra_ya_entregada(bd: Session, carpeta) -> None:
    """Con miércoles 02/12 feriado, 3 días hábiles antes del viernes 04/12 es el lunes 30/11. Si la
    obra ya tiene un paquete exportado, deja de avisar."""
    from core.models.cadena import EslabonVersion
    from seguridad.modelo import EventoAcceso

    _vivienda_con_entrega(
        carpeta,
        date(2026, 12, 4),
        feriados=(date(2026, 12, 2),),
        linea_base=True,
    )
    avisos.fijar_preferencias(bd, _usuario(bd, "ana").id, [("compras", False)])
    _compras(bd, carpeta, "ana", date(2026, 11, 27))  # vie: 4 días hábiles antes
    assert _de(bd, "ana") == []
    _compras(bd, carpeta, "ana", date(2026, 11, 30))  # lun: 3 días hábiles antes
    assert [n.titulo for n in _de(bd, "ana")] == [ENTREGA_AVISO[1]]

    # Si el paquete de la versión ya se exportó, el día de entrega no emite Error de sin entregar.
    with abrir_sesion_caso(carpeta) as s:
        sello = s.scalar(select(EslabonVersion.huella_eslabon))
    assert sello is not None
    bd.add(
        EventoAcceso(
            tipo="paquete exportado",
            fecha_hora=datetime(2026, 12, 1, 12, 0),
            login_intentado="ana",
            ip_cliente="127.0.0.1",
            detalle=f"paq-1; version VIV-001; sello_version {sello}",
        )
    )
    bd.commit()
    _compras(bd, carpeta, "ana", date(2026, 12, 4))
    assert len(_de(bd, "ana")) == 1


def test_una_carpeta_que_no_abre_no_impide_el_recordatorio(bd: Session) -> None:
    _indice(bd, _fila(enviado_por=ANA))

    @contextmanager
    def rota():
        raise RuntimeError("la carpeta no abre")
        yield  # pragma: no cover

    _barrer(bd, "rosa", MARTES, rota)  # rosa arma y revisa: intenta compras y recuerda
    assert [n.clave_evento for n in _de(bd, "rosa")] == [
        "aprobacion:vivienda.db:1:VIV-001:recordatorio"
    ]


# --- categoría 4: listas de precios ---------------------------------------------------------------


def _lista(bd: Session, quien: str, lista_id: int = 7, caso: str | None = "vivienda.db") -> None:
    avisos.lista_cargada(
        bd,
        caso=caso,
        carpeta_empresa="silice.db",
        lista_id=lista_id,
        nombre="Lista Demo noviembre",
        quien=_cuenta(bd, quien),
        ahora=AHORA,
    )
    bd.commit()


def test_una_lista_nueva_llega_a_quienes_arman_menos_quien_la_cargo(bd: Session) -> None:
    _lista(bd, "admin")
    esperada = (
        "info",
        "Lista de precios nueva: «Lista Demo noviembre»",
        "Admin de Prueba la cargó en la carpeta «vivienda.db».",
        "Ver los precios de la empresa",
        "/precios/listas",
    )
    for login in ("ana", "tomas", "rosa"):
        assert [_forma(n) for n in _de(bd, login)] == [esperada], login
    assert _de(bd, "rita") == [] and _de(bd, "admin") == []
    assert _de(bd, "ana")[0].clave_evento == "lista:vivienda.db:7"
    _lista(bd, "admin")
    assert len(_de(bd, "ana")) == 1


def test_quien_carga_y_arma_no_se_avisa_y_la_empresa_se_nombra(bd: Session) -> None:
    _lista(bd, "rosa", lista_id=8, caso="silice.db")
    assert _de(bd, "rosa") == []
    assert _de(bd, "ana")[0].detalle == "Rosa la cargó en la carpeta de la empresa."


def test_la_lista_apagada_no_llega(bd: Session) -> None:
    avisos.fijar_preferencias(bd, _usuario(bd, "ana").id, [("listas_de_precios", False)])
    _lista(bd, "admin")
    assert _de(bd, "ana") == [] and len(_de(bd, "tomas")) == 1


def test_un_enlace_que_no_cabe_se_quita_y_el_aviso_llega(bd: Session) -> None:
    larga = "c" * 320 + ".db"
    _aprobaciones(bd, [], [_fila(caso=larga)])
    [aviso] = _de(bd, "rita")
    assert (aviso.titulo, aviso.enlace_texto, aviso.enlace_ruta) == (
        "VIV-001 de «Vivienda Demo 80 m2» espera su dictamen",
        "",
        "",
    )
    assert len(aviso.clave_evento) == 255  # la clave larga se acorta con su huella
