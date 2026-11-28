"""Registro con código de 20 caracteres (C9a; spec 2026-11-26-registro-con-codigo §4 y §7).

Oráculos a mano: la huella del código se recalcula aquí con `hashlib` (SHA-256 del código sin
guiones), los mensajes son los literales de la especificación y los límites (5 por equipo y hora,
50 pendientes, 7 días) se escriben como números, no se leen del módulo. Datos ficticios: personas
inventadas («Lucía Prueba», `lucia`) y correos de `ejemplo.com`.
"""

from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote

import pytest
from sqlalchemy import event, select

from seguridad import cuentas, solicitudes
from seguridad.modelo import EventoAcceso, IntentoAcceso, SolicitudCuenta, Usuario
from seguridad.permisos import PermisoDenegado
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, instalacion, persona

NOMBRE = "Lucía Prueba"
CORREO = "lucia@ejemplo.com"
LOGIN = "lucia"
CLAVE = "clave larga de lucia 2026"
MALA = "otra clave larga que no es"
MENSAJE_CANJE = "El usuario, la contraseña o el código no son válidos."
MENSAJE_LIMITE = (
    "Hay demasiadas solicitudes pendientes. Pida al administrador que revise las que hay."
)
MENSAJE_RECIBIDA = (
    "Su solicitud quedó registrada. Cuando el administrador la apruebe, le llegará un código de "
    "20 caracteres a su correo. Escríbalo en “Tengo un código”."
)
FORMATO = re.compile(r"^[A-Z2-7]{4}(-[A-Z2-7]{4}){4}$")
SIETE_DIAS = timedelta(days=7)
IP = "192.168.1.20"


class FrenoQueCuenta(cuentas.FrenoGlobal):
    """El freno de siempre, que además cuenta cuántos fallos se le registran."""

    def __init__(self) -> None:
        super().__init__()
        self.fallos = 0

    def registrar_fallo(self, ahora) -> None:
        self.fallos += 1
        super().registrar_fallo(ahora)


@pytest.fixture(autouse=True)
def _reiniciar_cupo():
    solicitudes.CUPO.reiniciar()
    yield
    solicitudes.CUPO.reiniciar()


@pytest.fixture
def freno() -> FrenoQueCuenta:
    return FrenoQueCuenta()


@pytest.fixture
def base(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        yield sesion, admin


def _huella(codigo: str) -> str:
    return hashlib.sha256(codigo.replace("-", "").encode("ascii")).hexdigest()


def _solicitar(sesion, login=LOGIN, *, ip=IP, cuando=AHORA, correo=CORREO, clave=CLAVE):
    return solicitudes.solicitar(sesion, NOMBRE, correo, login, clave, cuando, ip=ip)


def _aprobada(sesion, admin, papel="arma", cuando=AHORA):
    pedida = _solicitar(sesion, cuando=cuando)
    return pedida, solicitudes.aprobar(sesion, admin, pedida.id, papel, cuando)


def _canjear(sesion, codigo, freno, *, login=LOGIN, clave=CLAVE, cuando=AHORA):
    return solicitudes.canjear(
        sesion, login, clave, codigo, cuando, ip=IP, freno=freno, dormir=lambda _s: None
    )


def _ultimo_evento(sesion) -> EventoAcceso:
    return sesion.scalars(select(EventoAcceso).order_by(EventoAcceso.id.desc())).first()


def _pendientes_a_mano(sesion, cuantas: int) -> None:
    """Solicitudes pendientes escritas directo en la tabla (sin Argon2: solo cuentan)."""
    for i in range(cuantas):
        sesion.add(
            SolicitudCuenta(
                login=f"relleno{i:02d}",
                nombre="Relleno",
                correo="r@ejemplo.com",
                huella_clave="no-es-argon2",
                creada=AHORA,
                estado="pendiente",
            )
        )
    sesion.commit()


# --- solicitar ------------------------------------------------------------------------------


def test_solicitar_guarda_una_solicitud_pendiente_y_no_una_cuenta(base) -> None:
    sesion, _ = base
    pedida = _solicitar(sesion)
    assert (pedida.login, pedida.nombre, pedida.correo) == (LOGIN, NOMBRE, CORREO)
    assert (pedida.estado, pedida.papel, pedida.huella_codigo, pedida.vence) == (
        "pendiente",
        None,
        None,
        None,
    )
    assert pedida.creada == AHORA
    assert pedida.huella_clave.startswith("$argon2") and CLAVE not in pedida.huella_clave
    assert sesion.scalar(select(Usuario).where(Usuario.login == LOGIN)) is None
    evento = _ultimo_evento(sesion)
    assert (evento.tipo, evento.login_intentado, evento.ip_cliente) == ("solicitud", LOGIN, IP)
    assert CLAVE not in evento.detalle


def test_el_mensaje_de_recibida_es_el_de_la_especificacion() -> None:
    assert solicitudes.MENSAJE_RECIBIDA == MENSAJE_RECIBIDA


def test_el_login_se_normaliza(base) -> None:
    sesion, _ = base
    assert _solicitar(sesion, "  Lucia ").login == LOGIN


@pytest.mark.parametrize("ocupado", ["admin", "ADMIN"])
def test_un_login_de_una_cuenta_esta_en_uso(base, ocupado: str) -> None:
    sesion, _ = base
    with pytest.raises(solicitudes.LoginEnUso) as error:
        _solicitar(sesion, ocupado)
    assert str(error.value) == solicitudes.MENSAJE_EN_USO


@pytest.mark.parametrize("estado", ["pendiente", "aprobada"])
def test_un_login_de_una_solicitud_viva_esta_en_uso_con_el_mismo_mensaje(base, estado) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    if estado == "aprobada":
        solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA)
    with pytest.raises(solicitudes.LoginEnUso) as error:
        _solicitar(sesion, ip="10.0.0.9")
    assert str(error.value) == solicitudes.MENSAJE_EN_USO
    assert sesion.scalars(select(SolicitudCuenta)).all() == [pedida]


def test_un_login_rechazado_puede_volver_a_pedirse(base) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    solicitudes.rechazar(sesion, admin, pedida.id, AHORA)
    otra = _solicitar(sesion, correo="lucia2@ejemplo.com", cuando=AHORA + timedelta(hours=2))
    assert otra.id == pedida.id  # el login es único: la misma fila vuelve a empezar
    assert (otra.estado, otra.correo, otra.creada) == (
        "pendiente",
        "lucia2@ejemplo.com",
        AHORA + timedelta(hours=2),
    )
    assert otra.resuelta_por == ""


@pytest.mark.parametrize(
    "correo",
    [
        "",
        "sin-arroba.com",
        "dos@@ejemplo.com",
        "a@b@ejemplo.com",
        "lucia@ejemplo",
        "@ejemplo.com",
        "lucia@.com",
        "lucia@ejemplo.",
        "con espacio@ejemplo.com",
        "x" * 250 + "@e.com",
    ],
)
def test_un_correo_sin_forma_de_correo_se_rechaza(base, correo: str) -> None:
    sesion, _ = base
    with pytest.raises(ValueError, match="correo"):
        _solicitar(sesion, correo=correo)
    assert sesion.scalars(select(SolicitudCuenta)).all() == []


def test_la_contrasena_sigue_la_politica_de_siempre(base) -> None:
    sesion, _ = base
    with pytest.raises(cuentas.ContrasenaInvalida):
        _solicitar(sesion, clave="corta")
    with pytest.raises(cuentas.ContrasenaInvalida):
        _solicitar(sesion, "lucia.perez.2026", clave="lucia.perez.2026")
    with pytest.raises(ValueError, match="usuario"):
        _solicitar(sesion, "x")


def test_el_nombre_es_obligatorio(base) -> None:
    sesion, _ = base
    with pytest.raises(ValueError, match="nombre"):
        solicitudes.solicitar(sesion, "   ", CORREO, LOGIN, CLAVE, AHORA, ip=IP)


def test_cinco_por_equipo_en_una_hora_y_la_sexta_no(base) -> None:
    sesion, _ = base
    for i in range(5):
        _solicitar(sesion, f"persona{i}", cuando=AHORA + timedelta(minutes=i))
    with pytest.raises(solicitudes.DemasiadasSolicitudes) as error:
        _solicitar(sesion, "persona5", cuando=AHORA + timedelta(minutes=10))
    assert str(error.value) == MENSAJE_LIMITE
    # otro equipo sí puede, y el mismo, pasada la hora de la primera
    _solicitar(sesion, "persona6", ip="10.0.0.9", cuando=AHORA + timedelta(minutes=10))
    _solicitar(sesion, "persona7", cuando=AHORA + timedelta(hours=1))


def test_la_hora_del_limite_por_equipo_es_exacta(base) -> None:
    sesion, _ = base
    for i in range(5):
        _solicitar(sesion, f"persona{i}")
    with pytest.raises(solicitudes.DemasiadasSolicitudes):
        _solicitar(sesion, "persona5", cuando=AHORA + timedelta(minutes=59, seconds=59))
    _solicitar(sesion, "persona6", cuando=AHORA + timedelta(hours=1))


def test_cincuenta_pendientes_en_total_y_la_51_no(base) -> None:
    sesion, _ = base
    _pendientes_a_mano(sesion, 49)
    _solicitar(sesion)  # la 50
    with pytest.raises(solicitudes.DemasiadasSolicitudes) as error:
        _solicitar(sesion, "otra.persona", ip="10.0.0.9")
    assert str(error.value) == MENSAJE_LIMITE


def test_las_resueltas_no_cuentan_en_el_tope_de_pendientes(base) -> None:
    sesion, admin = base
    _pendientes_a_mano(sesion, 50)
    primera = sesion.scalars(select(SolicitudCuenta)).first()
    solicitudes.rechazar(sesion, admin, primera.id, AHORA)
    _solicitar(sesion)


# --- listar ---------------------------------------------------------------------------------


def test_solo_el_administrador_lista(base, tmp_path: Path) -> None:
    sesion, admin = base
    ana = persona(sesion, admin, "ana", ("arma",))
    with pytest.raises(PermisoDenegado):
        solicitudes.listar(sesion, ana, AHORA)


def test_listar_las_trae_todas_las_mas_nuevas_primero(base) -> None:
    sesion, admin = base
    vieja = _solicitar(sesion, "vieja")
    nueva = _solicitar(sesion, "nueva", cuando=AHORA + timedelta(minutes=5))
    assert [s.id for s in solicitudes.listar(sesion, admin, AHORA)] == [nueva.id, vieja.id]


def test_al_listar_las_aprobadas_que_vencieron_salen_vencidas_sin_escribir(base) -> None:
    """#9: GET /v1/solicitudes no escribe; el estado `vencida` se calcula al responder."""
    sesion, admin = base
    pedida, _ = _aprobada(sesion, admin)
    justo_antes = AHORA + SIETE_DIAS - timedelta(seconds=1)
    assert [s.estado for s in solicitudes.listar(sesion, admin, justo_antes)] == ["aprobada"]

    escrituras: list[str] = []
    motor = sesion.get_bind()

    def vigilar(_conn, _cursor, sentencia, *_resto) -> None:
        cabeza = sentencia.lstrip().upper()
        if cabeza.startswith(("INSERT", "UPDATE", "DELETE", "BEGIN IMMEDIATE")):
            escrituras.append(sentencia)

    event.listen(motor, "before_cursor_execute", vigilar)
    try:
        vistas = solicitudes.listar(sesion, admin, AHORA + SIETE_DIAS)
    finally:
        event.remove(motor, "before_cursor_execute", vigilar)
    assert [s.estado for s in vistas] == ["vencida"]
    assert escrituras == []
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, pedida.id).estado == "aprobada"


# --- aprobar --------------------------------------------------------------------------------


def test_aprobar_da_un_codigo_de_20_con_formato_y_guarda_solo_su_huella(base) -> None:
    sesion, admin = base
    pedida, aprobacion = _aprobada(sesion, admin, "revisa")
    assert FORMATO.fullmatch(aprobacion.codigo)
    assert aprobacion.vence == AHORA + SIETE_DIAS
    sesion.expire_all()
    fila = sesion.get(SolicitudCuenta, pedida.id)
    assert (fila.estado, fila.papel, fila.vence) == ("aprobada", "revisa", AHORA + SIETE_DIAS)
    assert fila.huella_codigo == _huella(aprobacion.codigo)
    assert fila.resuelta_por == "Admin de Prueba <admin>"
    sin_guiones = aprobacion.codigo.replace("-", "")
    for valor in vars(fila).values():
        assert sin_guiones not in str(valor) and aprobacion.codigo not in str(valor)
    evento = _ultimo_evento(sesion)
    assert evento.tipo == "solicitud aprobada" and sin_guiones not in evento.detalle


def test_el_enlace_de_correo_lleva_destinatario_asunto_y_codigo(base) -> None:
    sesion, admin = base
    _, aprobacion = _aprobada(sesion, admin)
    assert aprobacion.mailto.startswith(f"mailto:{CORREO}?subject=")
    texto = unquote(aprobacion.mailto)
    assert aprobacion.codigo in texto and LOGIN in texto and "Tengo un código" in texto
    assert "17/11/2026" in texto  # vence: 10/11/2026 + 7 días, con la fecha de aquí


def test_un_correo_con_caracteres_de_url_no_agrega_cabeceras_al_enlace(base) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion, correo="lucia+obra@ejemplo.com")
    aprobacion = solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA)
    destinatario = aprobacion.mailto.removeprefix("mailto:").split("?", 1)[0]
    assert unquote(destinatario) == "lucia+obra@ejemplo.com"
    assert aprobacion.mailto.count("?") == 1 and "&bcc" not in aprobacion.mailto


def test_solo_el_administrador_aprueba(base) -> None:
    sesion, admin = base
    ana = persona(sesion, admin, "ana", ("arma",))
    pedida = _solicitar(sesion)
    with pytest.raises(PermisoDenegado):
        solicitudes.aprobar(sesion, ana, pedida.id, "arma", AHORA)
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, pedida.id).estado == "pendiente"


@pytest.mark.parametrize("papel", ["administrador", "", "ARMA ", "otro"])
def test_el_papel_es_arma_o_revisa(base, papel: str) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    with pytest.raises(ValueError, match="papel"):
        solicitudes.aprobar(sesion, admin, pedida.id, papel, AHORA)


def test_aprobar_una_que_no_existe_es_lookup(base) -> None:
    sesion, admin = base
    with pytest.raises(LookupError):
        solicitudes.aprobar(sesion, admin, 999, "arma", AHORA)


def test_una_rechazada_no_se_aprueba(base) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    solicitudes.rechazar(sesion, admin, pedida.id, AHORA)
    with pytest.raises(solicitudes.SolicitudResuelta):
        solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA)


def test_si_el_login_ya_es_una_cuenta_no_se_aprueba(base) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    # Desde el hallazgo #7, crear_usuario ya no deja dar de alta ese login; este estado solo llega
    # por una base anterior o una escritura directa, y aprobar lo sigue rechazando.
    sesion.add(
        Usuario(
            login=LOGIN,
            nombre="Lucía",
            huella_clave="x",
            roles="arma",
            activo=True,
            creado=AHORA,
            creado_por="prueba",
        )
    )
    sesion.commit()
    with pytest.raises(solicitudes.LoginEnUso):
        solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA)


def test_reaprobar_invalida_el_codigo_anterior(base, freno) -> None:
    sesion, admin = base
    pedida, primera = _aprobada(sesion, admin)
    segunda = solicitudes.aprobar(sesion, admin, pedida.id, "revisa", AHORA + timedelta(hours=1))
    assert segunda.codigo != primera.codigo
    assert segunda.vence == AHORA + timedelta(hours=1) + SIETE_DIAS
    with pytest.raises(cuentas.ErrorDeAcceso):
        _canjear(sesion, primera.codigo, freno)
    assert _canjear(sesion, segunda.codigo, freno).roles == "revisa"


def test_una_vencida_se_vuelve_a_aprobar_con_un_codigo_nuevo(base, freno) -> None:
    sesion, admin = base
    pedida, primera = _aprobada(sesion, admin)
    despues = AHORA + SIETE_DIAS
    solicitudes.listar(sesion, admin, despues)
    nueva = solicitudes.aprobar(sesion, admin, pedida.id, "arma", despues)
    with pytest.raises(cuentas.ErrorDeAcceso):
        _canjear(sesion, primera.codigo, freno, cuando=despues)
    assert _canjear(sesion, nueva.codigo, freno, cuando=despues).login == LOGIN


# --- rechazar -------------------------------------------------------------------------------


def test_rechazar_la_cierra_y_borra_su_codigo(base, freno) -> None:
    sesion, admin = base
    pedida, aprobacion = _aprobada(sesion, admin)
    solicitudes.rechazar(sesion, admin, pedida.id, AHORA)
    sesion.expire_all()
    fila = sesion.get(SolicitudCuenta, pedida.id)
    assert (fila.estado, fila.huella_codigo, fila.vence) == ("rechazada", None, None)
    assert fila.resuelta_por == "Admin de Prueba <admin>"
    assert _ultimo_evento(sesion).tipo == "solicitud rechazada"
    with pytest.raises(cuentas.ErrorDeAcceso):
        _canjear(sesion, aprobacion.codigo, freno)


def test_solo_el_administrador_rechaza(base) -> None:
    sesion, admin = base
    rita = persona(sesion, admin, "rita", ("revisa",))
    pedida = _solicitar(sesion)
    with pytest.raises(PermisoDenegado):
        solicitudes.rechazar(sesion, rita, pedida.id, AHORA)


def test_una_usada_no_se_rechaza(base, freno) -> None:
    sesion, admin = base
    pedida, aprobacion = _aprobada(sesion, admin)
    _canjear(sesion, aprobacion.codigo, freno)
    with pytest.raises(solicitudes.SolicitudResuelta):
        solicitudes.rechazar(sesion, admin, pedida.id, AHORA)


# --- canjear --------------------------------------------------------------------------------


def test_canjear_crea_la_cuenta_con_su_papel_y_la_solicitud_queda_usada(base, freno) -> None:
    sesion, admin = base
    pedida, aprobacion = _aprobada(sesion, admin)
    cuando = AHORA + timedelta(days=2)
    usuario = _canjear(sesion, aprobacion.codigo.lower(), freno, cuando=cuando)
    assert (usuario.login, usuario.nombre, usuario.correo, usuario.roles) == (
        LOGIN,
        NOMBRE,
        CORREO,
        "arma",
    )
    assert usuario.activo and not usuario.debe_cambiar_clave and not usuario.restablecida_por_admin
    assert (usuario.creado, usuario.creado_por) == (cuando, "Admin de Prueba <admin>")
    sesion.expire_all()
    fila = sesion.get(SolicitudCuenta, pedida.id)
    assert (fila.estado, fila.huella_codigo) == ("usada", None)
    evento = _ultimo_evento(sesion)
    assert (evento.tipo, evento.usuario_id) == ("codigo canjeado", usuario.id)
    # la cuenta entra con su contraseña, como cualquier otra
    assert (
        cuentas.autenticar(sesion, LOGIN, CLAVE, cuando, freno=freno, dormir=lambda _s: None).id
        == usuario.id
    )


def test_un_segundo_canje_del_mismo_codigo_falla(base, freno) -> None:
    sesion, admin = base
    _, aprobacion = _aprobada(sesion, admin)
    _canjear(sesion, aprobacion.codigo, freno)
    with pytest.raises(cuentas.ErrorDeAcceso) as error:
        _canjear(sesion, aprobacion.codigo, freno)
    assert str(error.value) == MENSAJE_CANJE
    assert _ultimo_evento(sesion).detalle == "solicitud usada"


def test_un_dia_antes_de_vencer_vale_y_a_los_7_dias_exactos_no(base, freno) -> None:
    sesion, admin = base
    pedida_vencida, aprobacion = _aprobada(sesion, admin)
    with pytest.raises(cuentas.ErrorDeAcceso) as error:
        _canjear(sesion, aprobacion.codigo, freno, cuando=AHORA + SIETE_DIAS)
    assert str(error.value) == MENSAJE_CANJE
    assert _ultimo_evento(sesion).detalle == "codigo vencido"
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, pedida_vencida.id).estado == "vencida"
    otra = _solicitar(sesion, "lucia.vigente", ip="10.0.0.9")
    aprobada_vigente = solicitudes.aprobar(sesion, admin, otra.id, "arma", AHORA)
    ultimo_segundo = AHORA + SIETE_DIAS - timedelta(seconds=1)
    assert (
        _canjear(
            sesion, aprobada_vigente.codigo, freno, login="lucia.vigente", cuando=ultimo_segundo
        ).login
        == "lucia.vigente"
    )


def _fallo(sesion, freno, codigo, **extra) -> str:
    with pytest.raises(cuentas.ErrorDeAcceso) as error:
        _canjear(sesion, codigo, freno, **extra)
    assert type(error.value) is cuentas.ErrorDeAcceso
    return str(error.value)


def test_todos_los_fallos_dan_el_mismo_mensaje(base, freno) -> None:
    sesion, admin = base
    _, aprobacion = _aprobada(sesion, admin)
    _solicitar(sesion, "sin.aprobar", ip="10.0.0.9")
    ajeno = "AAAA-BBBB-CCCC-DDDD-EEEE"
    mensajes = {
        _fallo(sesion, freno, ajeno),  # código ajeno
        _fallo(sesion, freno, aprobacion.codigo, clave=MALA),  # contraseña mala
        _fallo(sesion, freno, aprobacion.codigo, login="nadie"),  # sin solicitud
        _fallo(sesion, freno, aprobacion.codigo, login="sin.aprobar"),  # pendiente
        _fallo(sesion, freno, aprobacion.codigo, cuando=AHORA + SIETE_DIAS),  # vencido
    }
    assert mensajes == {MENSAJE_CANJE}
    assert sesion.scalar(select(Usuario).where(Usuario.login == LOGIN)) is None


def test_el_codigo_de_otra_solicitud_no_sirve(base, freno) -> None:
    sesion, admin = base
    _, mio = _aprobada(sesion, admin)
    otra = _solicitar(sesion, "otra.persona")
    suyo = solicitudes.aprobar(sesion, admin, otra.id, "arma", AHORA)
    assert _fallo(sesion, freno, suyo.codigo) == MENSAJE_CANJE
    assert _ultimo_evento(sesion).detalle == "codigo"
    assert _canjear(sesion, mio.codigo, freno).login == LOGIN


def test_cada_fallo_cuenta_en_el_contador_del_login_y_en_el_freno(base, freno) -> None:
    sesion, admin = base
    _, aprobacion = _aprobada(sesion, admin)
    for intento in range(1, 5):
        _fallo(sesion, freno, aprobacion.codigo, clave=MALA)
        assert sesion.get(IntentoAcceso, LOGIN).fallos_seguidos == intento
        assert freno.fallos == intento
    with pytest.raises(cuentas.CuentaBloqueada):  # el quinto bloquea, como al entrar
        _canjear(sesion, aprobacion.codigo, freno, clave=MALA)
    with pytest.raises(cuentas.CuentaBloqueada):  # y bloqueado, ni el bueno pasa
        _canjear(sesion, aprobacion.codigo, freno)


def test_un_canje_bueno_reinicia_el_contador(base, freno) -> None:
    sesion, admin = base
    _, aprobacion = _aprobada(sesion, admin)
    _fallo(sesion, freno, aprobacion.codigo, clave=MALA)
    _canjear(sesion, aprobacion.codigo, freno)
    assert sesion.get(IntentoAcceso, LOGIN).fallos_seguidos == 0


def test_con_el_freno_activo_el_canje_espera(base) -> None:
    sesion, admin = base
    _, aprobacion = _aprobada(sesion, admin)
    freno = cuentas.FrenoGlobal()
    for _ in range(20):
        freno.registrar_fallo(AHORA)
    esperas: list[float] = []
    solicitudes.canjear(
        sesion, LOGIN, CLAVE, aprobacion.codigo, AHORA, freno=freno, dormir=esperas.append
    )
    assert esperas == [1.0]


# --- el orden de las comprobaciones: estado, vence, código y contraseña ---------------------


def test_vencida_y_con_el_codigo_ajeno_se_rechaza_por_vencida(base, freno) -> None:
    sesion, admin = base
    _aprobada(sesion, admin)
    _fallo(sesion, freno, "AAAA-BBBB-CCCC-DDDD-EEEE", cuando=AHORA + SIETE_DIAS)
    assert _ultimo_evento(sesion).detalle == "codigo vencido"


def test_pendiente_se_rechaza_por_su_estado_antes_que_por_el_codigo(base, freno) -> None:
    sesion, _ = base
    _solicitar(sesion)
    _fallo(sesion, freno, "AAAA-BBBB-CCCC-DDDD-EEEE", clave=MALA)
    assert _ultimo_evento(sesion).detalle == "solicitud pendiente"


def test_con_el_codigo_ajeno_la_contrasena_ni_se_verifica(
    base, freno, monkeypatch: pytest.MonkeyPatch
) -> None:
    sesion, admin = base
    _aprobada(sesion, admin)
    verificadas: list[str] = []
    original = solicitudes._coincide
    monkeypatch.setattr(
        solicitudes, "_coincide", lambda h, c: verificadas.append(c) or original(h, c)
    )
    _fallo(sesion, freno, "AAAA-BBBB-CCCC-DDDD-EEEE", clave=MALA)
    assert _ultimo_evento(sesion).detalle == "codigo"
    assert verificadas == []


def test_con_el_codigo_bueno_y_la_contrasena_mala_se_rechaza_por_la_contrasena(base, freno) -> None:
    sesion, admin = base
    _, aprobacion = _aprobada(sesion, admin)
    _fallo(sesion, freno, aprobacion.codigo, clave=MALA)
    assert _ultimo_evento(sesion).detalle == "contrasena"


# --- sin secretos en el registro ------------------------------------------------------------


def test_ningun_evento_lleva_el_codigo_ni_la_contrasena(base, freno) -> None:
    sesion, admin = base
    pedida, aprobacion = _aprobada(sesion, admin)
    _fallo(sesion, freno, aprobacion.codigo, clave=MALA)
    _canjear(sesion, aprobacion.codigo, freno)
    otra = _solicitar(sesion, "otra.persona")
    solicitudes.rechazar(sesion, admin, otra.id, AHORA)
    sin_guiones = aprobacion.codigo.replace("-", "")
    tipos = set()
    for evento in sesion.scalars(select(EventoAcceso)):
        tipos.add(evento.tipo)
        for campo in (evento.detalle, evento.login_intentado):
            for secreto in (CLAVE, MALA, aprobacion.codigo, sin_guiones, CONTRASENA):
                assert secreto not in campo, (evento.tipo, campo)
    assert {
        "solicitud",
        "solicitud aprobada",
        "solicitud rechazada",
        "codigo canjeado",
        "codigo rechazado",
    } <= tipos
    assert pedida.id


# --- revisión de seguridad de C9a (2026-11-26) ----------------------------------------------

# #1: el 409 también gasta cupo, para que no sirva de oráculo ilimitado de qué logins existen


def test_el_sexto_409_del_mismo_equipo_en_una_hora_da_429(base) -> None:
    sesion, _ = base
    for i in range(5):
        with pytest.raises(solicitudes.LoginEnUso):
            _solicitar(sesion, "admin", cuando=AHORA + timedelta(minutes=i))
    with pytest.raises(solicitudes.DemasiadasSolicitudes):
        _solicitar(sesion, "admin", cuando=AHORA + timedelta(minutes=10))
    with pytest.raises(solicitudes.DemasiadasSolicitudes):  # tampoco un login libre
        _solicitar(sesion, "libre", cuando=AHORA + timedelta(minutes=10))
    _solicitar(sesion, "libre", ip="10.0.0.9", cuando=AHORA + timedelta(minutes=10))


def test_un_login_en_uso_deja_rastro_en_los_eventos(base) -> None:
    sesion, _ = base
    with pytest.raises(solicitudes.LoginEnUso):
        _solicitar(sesion, "admin")
    evento = _ultimo_evento(sesion)
    assert (evento.tipo, evento.login_intentado, evento.ip_cliente, evento.detalle) == (
        "solicitud fallida",
        "admin",
        IP,
        "login en uso",
    )
    assert CLAVE not in evento.detalle
    assert sesion.scalars(select(SolicitudCuenta)).all() == []


def test_los_409_y_las_acertadas_suman_en_el_mismo_cupo(base) -> None:
    sesion, _ = base
    for i in range(3):
        _solicitar(sesion, f"persona{i}")
    for _ in range(2):
        with pytest.raises(solicitudes.LoginEnUso):
            _solicitar(sesion, "persona0")
    with pytest.raises(solicitudes.DemasiadasSolicitudes):
        _solicitar(sesion, "persona9")


# #2: el correo, solo ASCII y con la forma de RFC 5322 (dot-atom y dominio con etiquetas)


@pytest.mark.parametrize(
    "correo",
    [
        "maria@empresа.com",  # «а» cirílica
        "Maria<ataque@evil.com>",
        "x,ataque@evil.com",
        "maria%40empresa.com@evil.com",
        "maría@empresa.com",
        ".maria@empresa.com",
        "maria.@empresa.com",
        "ma..ria@empresa.com",
        "maria@-empresa.com",
        "maria@empresa-.com",
        "maria@empresa.c",
        "maria@empresa.c0m",
        "maria@empresa..com",
        'ma"ria@empresa.com',
        "maria;x@empresa.com",
        "maria@[127.0.0.1]",
        "maria(x)@empresa.com",
        "maria" + chr(92) + "x@empresa.com",  # barra invertida
        "maria:x@empresa.com",
        "maria@" + "a" * 64 + ".com",
        "a" * 65 + "@empresa.com",
    ],
)
def test_un_correo_fuera_de_la_forma_estricta_se_rechaza(base, correo: str) -> None:
    sesion, _ = base
    with pytest.raises(ValueError, match="correo"):
        _solicitar(sesion, correo=correo)


@pytest.mark.parametrize(
    ("correo", "guardado"),
    [
        ("maria@empresa.com", "maria@empresa.com"),
        ("Maria.Perez@Empresa.COM", "Maria.Perez@empresa.com"),
        ("lucia+obra@ejemplo.com.ve", "lucia+obra@ejemplo.com.ve"),
        ("o'brien_2@mi-empresa.co", "o'brien_2@mi-empresa.co"),
        ("  ana@ejemplo.com  ", "ana@ejemplo.com"),
        ("a" * 64 + "@" + "b" * 63 + ".com", "a" * 64 + "@" + "b" * 63 + ".com"),
    ],
)
def test_un_correo_valido_se_guarda_con_el_dominio_en_minusculas(base, correo, guardado) -> None:
    sesion, _ = base
    assert _solicitar(sesion, correo=correo).correo == guardado


# #3: el nombre, sin caracteres invisibles ni de control y sin forma de fórmula


@pytest.mark.parametrize(
    "nombre",
    [
        "Lucía\x00Prueba",
        "Lucía ‮abeurP",  # invierte el texto que sigue
        "​",  # espacio de ancho cero, solo
        "Lucía​Prueba",
        '=HYPERLINK("http://evil.example","clic")',
        "+58 412",
        "-Lucía",
        "@Lucía",
        "12345",
        "Lucía",  # uso privado
        "Lucía￾X",  # no asignado
    ],
)
def test_un_nombre_peligroso_o_sin_letras_se_rechaza(base, nombre: str) -> None:
    sesion, _ = base
    with pytest.raises(ValueError, match="nombre"):
        solicitudes.solicitar(sesion, nombre, CORREO, LOGIN, CLAVE, AHORA, ip=IP)


def test_el_nombre_se_normaliza_a_nfc(base) -> None:
    sesion, _ = base
    descompuesto = "Lucía  Prueba"  # «i» + acento combinante
    pedida = solicitudes.solicitar(sesion, descompuesto, CORREO, LOGIN, CLAVE, AHORA, ip=IP)
    assert pedida.nombre == "Lucía Prueba" and len(pedida.nombre) == 12


def test_un_nombre_con_guion_o_arroba_dentro_vale(base) -> None:
    sesion, _ = base
    assert _solicitar_con_nombre(sesion, "María-José O'Neil").nombre == "María-José O'Neil"


def _solicitar_con_nombre(sesion, nombre):
    return solicitudes.solicitar(sesion, nombre, CORREO, LOGIN, CLAVE, AHORA, ip=IP)


# #7: el alta por el administrador no pisa un login que una solicitud viva retiene


@pytest.mark.parametrize("estado", ["pendiente", "aprobada"])
def test_crear_usuario_rechaza_el_login_de_una_solicitud_viva(base, estado) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    if estado == "aprobada":
        solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA)
    with pytest.raises(ValueError) as error:
        persona(sesion, admin, LOGIN, ("revisa",))
    assert str(error.value) == f"Ya existe una cuenta con el usuario {LOGIN!r}."
    assert sesion.scalar(select(Usuario).where(Usuario.login == LOGIN)) is None


@pytest.mark.parametrize("como", ["rechazada", "vencida"])
def test_crear_usuario_puede_usar_el_login_de_una_solicitud_muerta(base, como) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    if como == "rechazada":
        solicitudes.rechazar(sesion, admin, pedida.id, AHORA)
        cuando = AHORA
    else:
        solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA)
        cuando = AHORA + SIETE_DIAS
    usuario = cuentas.crear_usuario(sesion, admin, LOGIN, NOMBRE, ("arma",), CONTRASENA, cuando)
    assert usuario.login == LOGIN


# --- hallazgos bajos e informativos de C9a (lote G4) ----------------------------------------

# #4: cupo en memoria tomado y sumado ANTES de Argon2, e IPv6 agrupada por /64


def test_el_cupo_en_memoria_se_cuenta_antes_de_argon2(
    base, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cinco intentos que abortan en Argon2 (cero filas en `evento_acceso`) ya llenan el cupo en
    memoria: el sexto se rechaza sin llamar a `_huella`."""
    sesion, _ = base
    llamadas: list[str] = []

    def huella_que_aborta(contrasena: str) -> str:
        llamadas.append(contrasena)
        raise RuntimeError("corte antes de escribir")

    monkeypatch.setattr(solicitudes, "_huella", huella_que_aborta)
    for i in range(5):
        with pytest.raises(RuntimeError, match="corte antes de escribir"):
            _solicitar(sesion, f"persona{i}")
    assert len(llamadas) == 5
    assert sesion.scalars(select(EventoAcceso).where(EventoAcceso.tipo == "solicitud")).all() == []
    with pytest.raises(solicitudes.DemasiadasSolicitudes) as error:
        _solicitar(sesion, "persona5")
    assert str(error.value) == MENSAJE_LIMITE
    assert len(llamadas) == 5


def test_ipv6_del_mismo_prefijo_64_comparten_cupo_y_otro_64_no(base) -> None:
    sesion, _ = base
    for i in range(5):
        _solicitar(sesion, f"ipv6.p{i}", ip=f"2001:db8:abcd:0001::{i + 1:x}")
    with pytest.raises(solicitudes.DemasiadasSolicitudes) as error:
        _solicitar(sesion, "ipv6.sexta", ip="2001:db8:abcd:0001:ffff:1234::9")
    assert str(error.value) == MENSAJE_LIMITE
    # otro prefijo /64 sí puede
    creada = _solicitar(sesion, "ipv6.otro64", ip="2001:db8:abcd:0002::1")
    assert creada.login == "ipv6.otro64"


def test_exigir_cupo_en_la_base_tambien_agrupa_ipv6_por_64(base) -> None:
    """Aunque el contador en memoria nazca limpio (reinicio del proceso), `_exigir_cupo` agrupa
    los eventos de la base por `/64` en IPv6."""
    sesion, _ = base
    for i in range(5):
        _solicitar(sesion, f"reinicio.p{i}", ip=f"2001:db8:cafe:0010::{i + 1:x}")
    cupo_nuevo = solicitudes.CupoPorEquipo()
    with pytest.raises(solicitudes.DemasiadasSolicitudes) as error:
        solicitudes.solicitar(
            sesion,
            NOMBRE,
            CORREO,
            "reinicio.sexta",
            CLAVE,
            AHORA + timedelta(minutes=5),
            ip="2001:db8:cafe:0010:9999::7",
            cupo=cupo_nuevo,
        )
    assert str(error.value) == MENSAJE_LIMITE
    # otro /64 pasa incluso con el cupo nuevo
    creada = solicitudes.solicitar(
        sesion,
        NOMBRE,
        CORREO,
        "reinicio.otro64",
        CLAVE,
        AHORA + timedelta(minutes=5),
        ip="2001:db8:cafe:0011::1",
        cupo=cupo_nuevo,
    )
    assert creada.login == "reinicio.otro64"


def test_ipv4_mapeada_en_ipv6_comparte_cupo_con_ipv4(base) -> None:
    sesion, _ = base
    for i in range(5):
        _solicitar(sesion, f"mapeada{i}", ip=IP)
    with pytest.raises(solicitudes.DemasiadasSolicitudes):
        _solicitar(sesion, "mapeada5", ip=f"::ffff:{IP}")


def test_cupo_en_memoria_se_libera_a_la_hora_exacta() -> None:
    cupo = solicitudes.CupoPorEquipo()
    for _ in range(5):
        assert cupo.tomar("2001:db8:1:2::1", AHORA) is True
    assert cupo.tomar("2001:db8:1:2:aaaa::2", AHORA + timedelta(minutes=59, seconds=59)) is False
    assert cupo.tomar("2001:db8:1:2:bbbb::3", AHORA + timedelta(hours=1)) is True


# #5: la aprobación guarda `resuelta_por_id` y no sobrevive si quien la dio dejó de ser admin activo


def test_aprobar_y_rechazar_guardan_resuelta_por_id(base) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    assert pedida.resuelta_por_id is None
    solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA)
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, pedida.id).resuelta_por_id == admin.id
    solicitudes.rechazar(sesion, admin, pedida.id, AHORA)
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, pedida.id).resuelta_por_id == admin.id
    otra = _solicitar(sesion, cuando=AHORA + timedelta(hours=2))
    assert otra.resuelta_por_id is None


def test_canjear_falla_si_quien_aprobo_fue_desactivado(
    base, freno, monkeypatch: pytest.MonkeyPatch
) -> None:
    sesion, admin = base
    admin2 = persona(sesion, admin, "admin2", ("administrador",))
    _, aprobacion = _aprobada(sesion, admin2)
    cuentas.desactivar(sesion, admin, admin2.id, AHORA + timedelta(minutes=5))
    verificadas: list[str] = []
    original = solicitudes._coincide
    monkeypatch.setattr(
        solicitudes, "_coincide", lambda h, c: verificadas.append(c) or original(h, c)
    )
    assert _fallo(sesion, freno, aprobacion.codigo, cuando=AHORA + timedelta(minutes=10)) == (
        MENSAJE_CANJE
    )
    assert _ultimo_evento(sesion).detalle == "aprobador revocado"
    assert verificadas == []
    assert freno.fallos == 1
    assert sesion.scalar(select(Usuario).where(Usuario.login == LOGIN)) is None


def test_canjear_falla_si_quien_aprobo_perdio_el_rol_de_administrador(base, freno) -> None:
    sesion, admin = base
    admin2 = persona(sesion, admin, "admin2", ("administrador",))
    pedida, aprobacion = _aprobada(sesion, admin2)
    cuentas.cambiar_roles(sesion, admin, admin2.id, ("arma",), AHORA + timedelta(minutes=5))
    assert _fallo(sesion, freno, aprobacion.codigo, cuando=AHORA + timedelta(minutes=10)) == (
        MENSAJE_CANJE
    )
    assert _ultimo_evento(sesion).detalle == "aprobador revocado"
    # otro administrador activo puede volver a aprobarla y el código nuevo sí vale
    nueva = solicitudes.aprobar(sesion, admin, pedida.id, "arma", AHORA + timedelta(minutes=15))
    creada = _canjear(sesion, nueva.codigo, freno, cuando=AHORA + timedelta(minutes=20))
    assert creada.login == LOGIN


def test_canjear_falla_si_resuelta_por_id_es_nulo(base, freno) -> None:
    """Una aprobación heredada de una base anterior a `ins_0016` no tiene aprobador verificable."""
    sesion, admin = base
    pedida, aprobacion = _aprobada(sesion, admin)
    pedida.resuelta_por_id = None
    sesion.commit()
    assert _fallo(sesion, freno, aprobacion.codigo) == MENSAJE_CANJE
    assert _ultimo_evento(sesion).detalle == "aprobador revocado"


# #6: reutilizar una rechazada o vencida deja historia en el evento y marca `reutilizada`


def test_reutilizar_una_rechazada_anota_la_historia_y_la_marca_reutilizada(base) -> None:
    sesion, admin = base
    pedida = _solicitar(sesion)
    assert [s.reutilizada for s in solicitudes.listar(sesion, admin, AHORA)] == [False]
    solicitudes.rechazar(sesion, admin, pedida.id, AHORA)
    _solicitar(sesion, correo="lucia2@ejemplo.com", cuando=AHORA + timedelta(hours=2))
    evento = _ultimo_evento(sesion)
    assert evento.tipo == "solicitud"
    assert evento.detalle == (
        "reutiliza una solicitud rechazada resuelta por Admin de Prueba <admin>"
    )
    vistas = solicitudes.listar(sesion, admin, AHORA + timedelta(hours=2))
    assert [(v.login, v.estado, v.reutilizada) for v in vistas] == [(LOGIN, "pendiente", True)]


def test_reutilizar_una_vencida_anota_la_historia_y_la_marca_reutilizada(base) -> None:
    """Incluso si nadie listó tras vencer (en la base aún dice `aprobada`), el detalle registra
    `vencida` y no `aprobada`."""
    sesion, admin = base
    _aprobada(sesion, admin)
    despues = AHORA + SIETE_DIAS + timedelta(minutes=1)
    _solicitar(sesion, correo="lucia3@ejemplo.com", cuando=despues)
    evento = _ultimo_evento(sesion)
    assert evento.tipo == "solicitud"
    assert evento.detalle == "reutiliza una solicitud vencida resuelta por Admin de Prueba <admin>"
    vistas = solicitudes.listar(sesion, admin, despues)
    assert [(v.login, v.estado, v.reutilizada) for v in vistas] == [(LOGIN, "pendiente", True)]


# #9: el estado `vencida` se persiste en aprobar, canjear y solicitar (nunca en listar)


def test_el_estado_vencida_se_persiste_en_aprobar_canjear_y_solicitar(base, freno) -> None:
    sesion, admin = base
    despues = AHORA + SIETE_DIAS

    # 1) Al aprobar otra solicitud, una aprobada ya vencida pasa a `vencida` en la base.
    v1, _ = _aprobada(sesion, admin)
    p2 = _solicitar(sesion, "segunda", ip="10.0.0.2")
    solicitudes.aprobar(sesion, admin, p2.id, "arma", despues)
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, v1.id).estado == "vencida"

    # 2) Al canjear (fallo por vencida o éxito de otra), las vencidas se persisten.
    v2 = _solicitar(sesion, "tercera", ip="10.0.0.3", cuando=despues)
    solicitudes.aprobar(sesion, admin, v2.id, "arma", despues)
    p3 = _solicitar(sesion, "cuarta", ip="10.0.0.4", cuando=despues + timedelta(days=1))
    ap3 = solicitudes.aprobar(sesion, admin, p3.id, "arma", despues + timedelta(days=1))
    _canjear(sesion, ap3.codigo, freno, login="cuarta", cuando=despues + SIETE_DIAS)
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, v2.id).estado == "vencida"

    # 3) Al solicitar una nueva cuenta, una aprobada ya vencida pasa a `vencida` en la base.
    v3 = _solicitar(sesion, "quinta", ip="10.0.0.5", cuando=despues + SIETE_DIAS)
    solicitudes.aprobar(sesion, admin, v3.id, "arma", despues + SIETE_DIAS)
    _solicitar(sesion, "sexta", ip="10.0.0.6", cuando=despues + SIETE_DIAS * 2)
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, v3.id).estado == "vencida"
