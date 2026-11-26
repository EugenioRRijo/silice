"""Registro con código de 20 caracteres (C9a; spec `2026-11-26-registro-con-codigo`).

Una persona pide una cuenta con su nombre, su correo, su usuario y su contraseña. Sílice guarda una
**solicitud** (`SolicitudCuenta`), no una cuenta: sin cuenta no hay sesión, y una sesión sin papel
no se puede escribir (spec §2). El administrador la aprueba con un papel (arma o revisa) y recibe,
una sola vez, un código de un solo uso que vence a los 7 días; de él solo se guarda el SHA-256. Al
canjearlo con el usuario y la contraseña, nace la cuenta con ese papel y la solicitud queda usada.

Todo lo que se puede reutilizar viene de `seguridad.cuentas` (el mismo paquete): la política de
usuario y contraseña, Argon2 con su semáforo, el contador por login (`IntentoAcceso`) con su bloqueo
de 15 minutos, el freno global, el bloqueo de escritura (`_tomar_escritura`) y el código (alfabeto,
generación, normalización y huella). Como en `cuentas`, cada función que cambia estado confirma su
propia transacción y el reloj (`ahora`) y la espera (`dormir`) se inyectan.

Decisiones que la especificación deja abiertas (anotadas en el informe de C9a):

- El tope «5 por equipo cada hora» cuenta los eventos `solicitud` de esa IP en la última hora (un
  evento de hace una hora exacta ya no cuenta): la tabla de la especificación no guarda la IP y el
  registro de accesos sí. Las 50 pendientes se cuentan en `solicitud_cuenta`.
- El login es único en `solicitud_cuenta`: una solicitud rechazada o vencida no retiene su login;
  pedirlo de nuevo reutiliza la fila, que vuelve a empezar como pendiente.
- El motivo de un canje rechazado (`sin solicitud`, `solicitud <estado>`, `codigo vencido`,
  `codigo`, `contrasena`) queda en el detalle del evento, que solo ve el administrador; a la persona
  siempre se le dice lo mismo. Nunca el código ni la contraseña.
"""

from __future__ import annotations

import hmac
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from seguridad import eventos
from seguridad.cuentas import (
    FRENO,
    MENSAJE_BLOQUEO,
    CuentaBloqueada,
    Dormir,
    ErrorDeAcceso,
    FrenoGlobal,
    _bloqueado,
    _coincide,
    _exigir_administrador,
    _fallar,
    _huella,
    _huella_codigo,
    _intento,
    _tomar_escritura,
    clave_de_intento,
    codigo_nuevo,
    formato_codigo,
    responsable_de,
    validar_contrasena,
    validar_login,
)
from seguridad.modelo import EventoAcceso, IntentoAcceso, SolicitudCuenta, Usuario
from seguridad.permisos import Rol, texto_de_roles
from seguridad.retencion import por_login, vigente, viva

VIGENCIA = timedelta(days=7)
VENTANA_POR_EQUIPO = timedelta(hours=1)
MAXIMO_POR_EQUIPO = 5
MAXIMO_PENDIENTES = 50
MAXIMO_NOMBRE = 120
MAXIMO_CORREO = 254
#: El papel que el administrador elige al aprobar: «Arma presupuestos» o «Revisa». El ascenso a
#: administrador sigue siendo `cuentas.cambiar_roles` (spec §1.5).
PAPELES: dict[str, Rol] = {"arma": Rol.ARMA, "revisa": Rol.REVISA}
#: Lo que el administrador aún puede aprobar (o volver a aprobar, con un código nuevo) o rechazar.
RESOLUBLES = frozenset({"pendiente", "aprobada", "vencida"})

MENSAJE_RECIBIDA = (
    "Su solicitud quedó registrada. Cuando el administrador la apruebe, le llegará un código de "
    "20 caracteres a su correo. Escríbalo en “Tengo un código”."
)
MENSAJE_LIMITE = (
    "Hay demasiadas solicitudes pendientes. Pida al administrador que revise las que hay."
)
MENSAJE_EN_USO = "Ese usuario ya está en uso; elija otro."
MENSAJE_CANJE = "El usuario, la contraseña o el código no son válidos."
MENSAJE_NOMBRE = f"Escriba su nombre (hasta {MAXIMO_NOMBRE} caracteres)."
MENSAJE_CORREO = "Escriba un correo válido, como nombre@empresa.com."
MENSAJE_PAPEL = "Elija el papel: arma presupuestos (arma) o revisa (revisa)."
MENSAJE_RESUELTA = "Esa solicitud ya se resolvió; no se puede cambiar."
MENSAJE_RECHAZADA = "Solicitud rechazada."
ASUNTO_DEL_CORREO = "Su código para entrar en Sílice"

MAXIMO_PARTE_LOCAL = 64
#: Lo que deja rastro y gasta cupo sin crear solicitud: un login en uso (revisión de seguridad #1).
TIPO_FALLIDA = "solicitud fallida"
#: Los eventos que gastan el cupo del equipo: la solicitud guardada y la que dio 409.
TIPOS_DEL_CUPO = ("solicitud", TIPO_FALLIDA)

#: La parte local como `dot-atom` de RFC 5322, solo ASCII y sin `%` (no se admite un
#: enrutamiento `a%b@c` que un servidor de correo podría reinterpretar).
_ATOMO = r"[A-Za-z0-9!#$&'*+/=?^_`{|}~-]+"
_PARTE_LOCAL = re.compile(rf"{_ATOMO}(?:\.{_ATOMO})*")
#: El dominio en minúsculas: etiquetas de 1 a 63 de `[a-z0-9-]` sin guion en los extremos, al
#: menos un punto y un dominio de nivel superior de 2 o más letras.
_ETIQUETA = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_DOMINIO = re.compile(rf"(?:{_ETIQUETA}\.)+[a-z]{{2,63}}")
#: Lo que un nombre no puede traer: control, formato (U+202E, U+200B...), sustitutos, uso
#: privado y sin asignar.
_CATEGORIAS_PROHIBIDAS = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})
#: Con qué no empieza un nombre: lo que una hoja de cálculo lee como fórmula.
_INICIOS_DE_FORMULA = ("=", "+", "-", "@")


class LoginEnUso(ValueError):  # noqa: N818
    """El login es de una cuenta o de una solicitud viva (el mismo mensaje en los dos casos)."""


class DemasiadasSolicitudes(ValueError):  # noqa: N818
    """Más de 5 solicitudes de un equipo en una hora, o 50 pendientes en total."""


class SolicitudResuelta(ValueError):  # noqa: N818
    """La solicitud ya se rechazó o se usó: no se aprueba ni se rechaza otra vez."""


@dataclass(frozen=True, slots=True)
class Aprobacion:
    """Lo que ve el administrador **una sola vez** al aprobar: el código con guiones, cuándo
    vence y el enlace `mailto:` ya escrito (C9a no sale a la red)."""

    codigo: str
    vence: datetime
    mailto: str


# --- validación -----------------------------------------------------------------------------


def validar_nombre(nombre: str) -> str:
    """El nombre en NFC y sin espacios de más. `ValueError` si trae un carácter de control, de
    formato (U+202E, U+200B), sustituto, de uso privado o sin asignar; si no tiene ninguna letra;
    si empieza por `=`, `+`, `-` o `@` (una hoja de cálculo lo leería como fórmula); o si pasa
    de 120 caracteres."""
    limpio = " ".join(unicodedata.normalize("NFC", nombre).split())
    if (
        not limpio
        or len(limpio) > MAXIMO_NOMBRE
        or any(unicodedata.category(c) in _CATEGORIAS_PROHIBIDAS for c in limpio)
        or not any(unicodedata.category(c).startswith("L") for c in limpio)
        or limpio.startswith(_INICIOS_DE_FORMULA)
    ):
        raise ValueError(MENSAJE_NOMBRE)
    return limpio


def validar_correo(correo: str) -> str:
    """El correo sin espacios alrededor y con el dominio en minúsculas, si es solo ASCII y tiene
    la forma estricta: una `@`; la parte local como `dot-atom` de RFC 5322 (hasta 64, sin punto en
    los extremos ni `..`, sin `<>,;:"()[]` ni `%` ni barra invertida); y el dominio por etiquetas
    (`_DOMINIO`); hasta 254 en total. Si no, `ValueError`. La forma no prueba que el correo
    exista: eso lo prueba el código que llega a él."""
    limpio = correo.strip()
    local, arroba, dominio = limpio.rpartition("@")
    dominio = dominio.lower()
    if (
        not limpio.isascii()
        or not arroba
        or len(limpio) > MAXIMO_CORREO
        or len(local) > MAXIMO_PARTE_LOCAL
        or not _PARTE_LOCAL.fullmatch(local)
        or not _DOMINIO.fullmatch(dominio)
    ):
        raise ValueError(MENSAJE_CORREO)
    return f"{local}@{dominio}"


def _login_libre(session: Session, login: str, ahora: datetime) -> SolicitudCuenta | None:
    """`LoginEnUso` si el login es de una cuenta o de una solicitud viva; si no, la solicitud
    muerta (rechazada, vencida) que se reutiliza, o `None`."""
    if session.scalar(select(Usuario.id).where(Usuario.login == login)) is not None:
        raise LoginEnUso(MENSAJE_EN_USO)
    previa = por_login(session, login, releer=True)
    if previa is not None and (viva(previa, ahora) or previa.estado == "usada"):
        raise LoginEnUso(MENSAJE_EN_USO)
    return previa


def _exigir_cupo(session: Session, ip: str, ahora: datetime) -> None:
    """`DemasiadasSolicitudes` con 5 intentos de este equipo en la última hora (las solicitudes
    guardadas y las que dieron 409; los de hace una hora exacta ya no cuentan) o con 50
    pendientes en total."""
    del_equipo = session.scalar(
        select(func.count())
        .select_from(EventoAcceso)
        .where(
            EventoAcceso.tipo.in_(TIPOS_DEL_CUPO),
            EventoAcceso.ip_cliente == ip,
            EventoAcceso.fecha_hora > ahora - VENTANA_POR_EQUIPO,
        )
    )
    pendientes = session.scalar(
        select(func.count())
        .select_from(SolicitudCuenta)
        .where(SolicitudCuenta.estado == "pendiente")
    )
    if del_equipo >= MAXIMO_POR_EQUIPO or pendientes >= MAXIMO_PENDIENTES:
        raise DemasiadasSolicitudes(MENSAJE_LIMITE)


# --- pedir una cuenta -----------------------------------------------------------------------


def _registrar_en_uso(session: Session, login: str, ip: str, ahora: datetime) -> None:
    """El 409 deja rastro y gasta cupo (`TIPOS_DEL_CUPO`): sin esto, probar logins ajenos no
    tendría límite. Toma el bloqueo de escritura (si aún no lo tenía) y confirma."""
    _tomar_escritura(session)
    eventos.registrar(session, TIPO_FALLIDA, ahora, login=login, ip=ip, detalle="login en uso")
    session.commit()


def solicitar(
    session: Session,
    nombre: str,
    correo: str,
    login: str,
    contrasena: str,
    ahora: datetime,
    *,
    ip: str = "",
) -> SolicitudCuenta:
    """Guarda una solicitud pendiente (no una cuenta). Valida con las reglas de siempre
    (`validar_login`, `validar_contrasena`), el nombre y la forma del correo (`ValueError`);
    `DemasiadasSolicitudes` pasado el tope y `LoginEnUso` si el login ya es de alguien. El tope y
    el login se miran antes de Argon2 (que un aluvión no pague 64 MiB por intento) y otra vez con
    el bloqueo de escritura tomado, que es lo que vale."""
    login_normal = validar_login(login)
    validar_contrasena(contrasena, login_normal)
    nombre_limpio = validar_nombre(nombre)
    correo_limpio = validar_correo(correo)
    _exigir_cupo(session, ip, ahora)
    try:
        _login_libre(session, login_normal, ahora)
    except LoginEnUso:
        _registrar_en_uso(session, login_normal, ip, ahora)
        raise
    session.rollback()  # solo se leyó: Argon2 corre sin el bloqueo
    huella = _huella(contrasena)
    _tomar_escritura(session)
    try:
        _exigir_cupo(session, ip, ahora)
        solicitud = _login_libre(session, login_normal, ahora)
    except LoginEnUso:
        _registrar_en_uso(session, login_normal, ip, ahora)
        raise
    except ValueError:
        session.rollback()
        raise
    if solicitud is None:
        solicitud = SolicitudCuenta(login=login_normal)
        session.add(solicitud)
    solicitud.nombre, solicitud.correo = nombre_limpio, correo_limpio
    solicitud.huella_clave = huella
    solicitud.creada, solicitud.estado, solicitud.resuelta_por = ahora, "pendiente", ""
    solicitud.papel = solicitud.huella_codigo = solicitud.vence = None
    eventos.registrar(session, "solicitud", ahora, login=login_normal, ip=ip)
    session.commit()
    return solicitud


# --- lo que hace el administrador -----------------------------------------------------------


def _como_administrador(session: Session, actor: Usuario) -> None:
    """Bloqueo de escritura y, ya tomado, el rol del actor leído de la base (pudo cambiar)."""
    _tomar_escritura(session)
    session.refresh(actor)
    try:
        _exigir_administrador(actor)
    except PermissionError:
        session.rollback()
        raise


def _resoluble(session: Session, solicitud_id: int) -> SolicitudCuenta:
    solicitud = session.get(SolicitudCuenta, solicitud_id, populate_existing=True)
    if solicitud is None:
        raise LookupError(f"no hay una solicitud con id {solicitud_id}")
    if solicitud.estado not in RESOLUBLES:
        raise SolicitudResuelta(MENSAJE_RESUELTA)
    return solicitud


def listar(session: Session, actor: Usuario, ahora: datetime) -> list[SolicitudCuenta]:
    """Todas las solicitudes, las más nuevas primero. Antes, las aprobadas cuyo código ya venció
    (`vence` ≤ `ahora`) pasan a `vencida`. Solo el administrador (`PermisoDenegado`)."""
    _como_administrador(session, actor)
    aprobadas = session.scalars(select(SolicitudCuenta).where(SolicitudCuenta.estado == "aprobada"))
    for solicitud in aprobadas:
        if not vigente(solicitud, ahora):
            solicitud.estado = "vencida"
    session.commit()
    return list(
        session.scalars(
            select(SolicitudCuenta).order_by(
                SolicitudCuenta.creada.desc(), SolicitudCuenta.id.desc()
            )
        )
    )


def enlace_de_correo(solicitud: SolicitudCuenta, codigo: str, vence: datetime) -> str:
    """El `mailto:` que abre el programa de correo del equipo con destinatario, asunto y el
    código en el cuerpo (C9a: Sílice no envía nada). Todo va codificado: un `?` o un `&` del
    correo no agrega cabeceras."""
    cuerpo = (
        f"Hola, {solicitud.nombre}:\r\n\r\n"
        "Su solicitud de cuenta en Sílice fue aprobada. En la pantalla de entrada pulse «Tengo un "
        f"código» y escriba su usuario ({solicitud.login}), su contraseña y este código:\r\n\r\n"
        f"{codigo}\r\n\r\n"
        f"El código sirve una sola vez y vence el {vence:%d/%m/%Y} a las {vence:%H:%M}.\r\n"
    )
    destinatario = quote(solicitud.correo, safe="@")
    return f"mailto:{destinatario}?subject={quote(ASUNTO_DEL_CORREO)}&body={quote(cuerpo)}"


def aprobar(
    session: Session, actor: Usuario, solicitud_id: int, papel: str, ahora: datetime
) -> Aprobacion:
    """Aprueba con `papel` (`arma` o `revisa`) y genera un código nuevo de un solo uso que vence
    a los 7 días; se guarda solo su SHA-256 y el anterior, si lo había, deja de valer. Una
    vencida se vuelve a aprobar igual. `ValueError` con otro papel, `LookupError` si no existe,
    `SolicitudResuelta` si se rechazó o se usó y `LoginEnUso` si el login ya es una cuenta."""
    if papel not in PAPELES:
        raise ValueError(MENSAJE_PAPEL)
    _como_administrador(session, actor)
    try:
        solicitud = _resoluble(session, solicitud_id)
        if session.scalar(select(Usuario.id).where(Usuario.login == solicitud.login)) is not None:
            raise LoginEnUso(MENSAJE_EN_USO)
    except (ValueError, LookupError):
        session.rollback()
        raise
    codigo = codigo_nuevo()
    vence = ahora + VIGENCIA
    solicitud.estado, solicitud.papel, solicitud.vence = "aprobada", papel, vence
    solicitud.huella_codigo = _huella_codigo(codigo)
    solicitud.resuelta_por = responsable_de(actor)
    eventos.registrar(
        session,
        "solicitud aprobada",
        ahora,
        login=solicitud.login,
        detalle=f"papel {papel}; por {actor.login}",
    )
    session.commit()
    formado = formato_codigo(codigo)
    mailto = enlace_de_correo(solicitud, formado, vence)
    return Aprobacion(codigo=formado, vence=vence, mailto=mailto)


def rechazar(
    session: Session, actor: Usuario, solicitud_id: int, ahora: datetime
) -> SolicitudCuenta:
    """Rechaza: su código, si lo tenía, deja de valer. `LookupError` si no existe y
    `SolicitudResuelta` si ya se rechazó o se usó."""
    _como_administrador(session, actor)
    try:
        solicitud = _resoluble(session, solicitud_id)
    except (ValueError, LookupError):
        session.rollback()
        raise
    solicitud.estado = "rechazada"
    solicitud.papel = solicitud.huella_codigo = solicitud.vence = None
    solicitud.resuelta_por = responsable_de(actor)
    eventos.registrar(
        session, "solicitud rechazada", ahora, login=solicitud.login, detalle=f"por {actor.login}"
    )
    session.commit()
    return solicitud


# --- canjear el código ----------------------------------------------------------------------


def _motivo_sin_contrasena(
    solicitud: SolicitudCuenta | None, codigo: str, ahora: datetime
) -> str | None:
    """Lo que se exige antes de la contraseña, en el orden de la especificación (§4): estado
    `aprobada`, `vence` > ahora y la huella del código. `None` si todo eso vale."""
    if solicitud is None:
        return "sin solicitud"
    if solicitud.estado != "aprobada":
        return f"solicitud {solicitud.estado}"
    if not vigente(solicitud, ahora):
        return "codigo vencido"
    if not hmac.compare_digest(solicitud.huella_codigo or "", _huella_codigo(codigo)):
        return "codigo"
    return None


def canjear(
    session: Session,
    login: str,
    contrasena: str,
    codigo: str,
    ahora: datetime,
    *,
    ip: str = "",
    freno: FrenoGlobal | None = None,
    dormir: Dormir = time.sleep,
) -> Usuario:
    """Crea la cuenta de una solicitud aprobada si el usuario, la contraseña y el código valen, y
    pasa la solicitud a `usada`, todo en una transacción con el bloqueo de escritura. Se exige, en
    este orden, estado `aprobada`, `vence` > ahora, la huella del código y la contraseña (Argon2,
    que solo corre si lo anterior vale). Cualquier fallo da `ErrorDeAcceso(MENSAJE_CANJE)` y cuenta
    en el contador del login y en el freno, como `cuentas.autenticar`; el quinto seguido bloquea
    (`CuentaBloqueada`). Confirma en todos los casos."""
    freno = FRENO if freno is None else freno
    espera = freno.espera(ahora)
    if espera:
        dormir(espera)
    clave = clave_de_intento(login)
    previa = por_login(session, clave)
    fila_previa = session.get(IntentoAcceso, clave)
    bloqueado_antes = (
        fila_previa is not None
        and fila_previa.bloqueado_hasta is not None
        and ahora < fila_previa.bloqueado_hasta
    )
    pasa = not bloqueado_antes and _motivo_sin_contrasena(previa, codigo, ahora) is None
    huella = previa.huella_clave if pasa else ""
    session.rollback()  # Argon2 corre sin el bloqueo de escritura
    correcta = pasa and _coincide(huella, contrasena)
    _tomar_escritura(session)
    fila = _intento(session, clave)
    if _bloqueado(fila, ahora):
        eventos.registrar(session, "bloqueo", ahora, login=clave, ip=ip, detalle="login bloqueado")
        session.commit()
        raise CuentaBloqueada(MENSAJE_BLOQUEO)
    solicitud = por_login(session, clave, releer=True)
    motivo = _motivo_sin_contrasena(solicitud, codigo, ahora)
    if motivo is None and not (correcta and solicitud.huella_clave == huella):
        motivo = "contrasena"
    existe = session.scalar(select(Usuario.id).where(Usuario.login == clave)) is not None
    if motivo is None and existe:
        motivo = "la cuenta ya existe"
    if motivo is not None:
        bloquea = _fallar(session, fila, ahora, freno)
        eventos.registrar(session, "codigo rechazado", ahora, login=clave, ip=ip, detalle=motivo)
        if bloquea:
            eventos.registrar(session, "bloqueo", ahora, login=clave, ip=ip, detalle="5 fallos")
        session.commit()
        raise CuentaBloqueada(MENSAJE_BLOQUEO) if bloquea else ErrorDeAcceso(MENSAJE_CANJE)
    usuario = Usuario(
        login=solicitud.login,
        nombre=solicitud.nombre,
        correo=solicitud.correo,
        huella_clave=solicitud.huella_clave,
        roles=texto_de_roles([PAPELES[solicitud.papel]]),
        activo=True,
        debe_cambiar_clave=False,
        restablecida_por_admin=False,
        creado=ahora,
        creado_por=solicitud.resuelta_por,
    )
    session.add(usuario)
    session.flush()
    solicitud.estado, solicitud.huella_codigo = "usada", None
    fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
    eventos.registrar(
        session,
        "codigo canjeado",
        ahora,
        login=clave,
        usuario_id=usuario.id,
        ip=ip,
        detalle=f"papel {solicitud.papel}",
    )
    session.commit()
    return usuario
