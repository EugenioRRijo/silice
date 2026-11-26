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
from sqlalchemy import select

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


def test_al_listar_las_aprobadas_que_vencieron_pasan_a_vencida(base) -> None:
    sesion, admin = base
    pedida, _ = _aprobada(sesion, admin)
    justo_antes = AHORA + SIETE_DIAS - timedelta(seconds=1)
    assert [s.estado for s in solicitudes.listar(sesion, admin, justo_antes)] == ["aprobada"]
    assert [s.estado for s in solicitudes.listar(sesion, admin, AHORA + SIETE_DIAS)] == ["vencida"]
    sesion.expire_all()
    assert sesion.get(SolicitudCuenta, pedida.id).estado == "vencida"


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
    _, aprobacion = _aprobada(sesion, admin)
    with pytest.raises(cuentas.ErrorDeAcceso) as error:
        _canjear(sesion, aprobacion.codigo, freno, cuando=AHORA + SIETE_DIAS)
    assert str(error.value) == MENSAJE_CANJE
    assert _ultimo_evento(sesion).detalle == "codigo vencido"
    ultimo_segundo = AHORA + SIETE_DIAS - timedelta(seconds=1)
    assert _canjear(sesion, aprobacion.codigo, freno, cuando=ultimo_segundo).login == LOGIN


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
