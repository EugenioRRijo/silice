"""Cuentas locales, contraseñas, bloqueo y primer administrador (spec S3 §5.2, §5.4, §5.5).

Contraseñas solo como Argon2 (`argon2-cffi`, parámetros por defecto de la biblioteca) con un
semáforo que limita las verificaciones simultáneas: cada una usa unos 64 MiB (SEG-11). Un login
inexistente se verifica igual contra una huella de relleno, con el mismo mensaje y el mismo
contador, para que ni el texto ni el tiempo delaten qué cuentas existen. Cinco fallos seguidos
bloquean el login 15 minutos; un freno global con espera progresiva cubre a quien recarga la
pestaña. Todo evento queda en `evento_acceso`, sin secretos.

Cada función que cambia estado **confirma su propia transacción** (la base de la instalación no
comparte transacción con ningún caso). El reloj `ahora` y la espera `dormir` se inyectan.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from seguridad import eventos, sesiones
from seguridad.modelo import CodigoInstalacion, IntentoAcceso, Usuario
from seguridad.permisos import Accion, PermisoDenegado, Rol, exigir, roles_de, texto_de_roles
from seguridad.secretos import CONTRASENAS_COMUNES

MENSAJE_FALLO = "Usuario o contraseña incorrectos."
MENSAJE_BLOQUEO = (
    "Demasiados intentos fallidos. Espere 15 minutos o pida al administrador que desbloquee "
    "la cuenta."
)
MENSAJE_BASE_OCUPADA = "La base está ocupada; reintente en unos segundos."
MENSAJE_CODIGO = "El código de instalación no es válido o ya se usó."
FALLOS_PARA_BLOQUEAR = 5
BLOQUEO = timedelta(minutes=15)
#: Un código de RESTABLECIMIENTO sirve menos de 24 h (a las 24:00 exactas ya no); el de la primera
#: vez no caduca (BCP-1, diseño §3.3).
CADUCIDAD_RESTABLECIMIENTO = timedelta(hours=24)
FRENO_FALLOS = 20
FRENO_VENTANA = timedelta(minutes=10)
FRENO_ESPERA_MAXIMA_S = 60.0
VERIFICACIONES_SIMULTANEAS = 4
MINIMO_CONTRASENA = 10
MAXIMO_CONTRASENA = 128
LONGITUD_CODIGO = 20
ALFABETO_CODIGO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # base32 (RFC 4648)
CLAVE_INTENTOS_CODIGO = "!codigo-de-instalacion"
NOMBRE_ARCHIVO_CODIGO = "codigo_instalacion.txt"
PATRON_LOGIN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
PURGA_DE_INEXISTENTES = timedelta(hours=24)
#: Lo que se guarda (evento y contador) cuando lo tecleado no puede ser un usuario.
LOGIN_NO_VALIDO = "(usuario no válido)"

_hasher = PasswordHasher()
_semaforo = threading.BoundedSemaphore(VERIFICACIONES_SIMULTANEAS)

Dormir = Callable[[float], None]


class ErrorDeAcceso(ValueError):  # noqa: N818
    """Usuario o contraseña incorrectos (el mismo mensaje exista o no el usuario)."""


class CuentaBloqueada(ErrorDeAcceso):  # noqa: N818
    """Cinco fallos seguidos: el mismo mensaje para un login inexistente."""


class ContrasenaInvalida(ValueError):  # noqa: N818
    """La contraseña no cumple la política (10 a 128, distinta del usuario, no común)."""


class FrenoGlobal:
    """Espera progresiva por fallos de todo el proceso (no de un login): 20 en 10 minutos y
    cada intento nuevo espera 1, 2, 4... s, hasta 60 s. Estado del proceso, no de un usuario
    (excepción declarada a la regla de S3 §4.4)."""

    def __init__(self) -> None:
        self._fallos: deque[datetime] = deque()
        self._candado = threading.Lock()

    def registrar_fallo(self, ahora: datetime) -> None:
        with self._candado:
            self._fallos.append(ahora)
            self._podar(ahora)

    def espera(self, ahora: datetime) -> float:
        with self._candado:
            self._podar(ahora)
            exceso = len(self._fallos) - FRENO_FALLOS
        if exceso < 0:
            return 0.0
        return float(min(FRENO_ESPERA_MAXIMA_S, 2**exceso))

    def reiniciar(self) -> None:
        with self._candado:
            self._fallos.clear()

    def _podar(self, ahora: datetime) -> None:
        while self._fallos and ahora - self._fallos[0] >= FRENO_VENTANA:
            self._fallos.popleft()


FRENO = FrenoGlobal()


# --- contraseñas y logins -------------------------------------------------------------------


def normalizar_login(login: str) -> str:
    return login.strip().casefold()


def validar_login(login: str) -> str:
    """El login normalizado, o `ValueError`: 3 a 40 caracteres a-z, 0-9, punto, guion."""
    normal = normalizar_login(login)
    if not PATRON_LOGIN.fullmatch(normal):
        raise ValueError("El usuario son 3 a 40 caracteres: letras, números, punto o guion.")
    return normal


def validar_contrasena(contrasena: str, login: str = "") -> None:
    """Política de S3 §5.2 (línea de NIST SP 800-63B, cita por verificar en S3-0): 10 a 128
    caracteres Unicode, distinta del usuario, fuera de la lista de comunes; sin reglas de
    composición."""
    if len(contrasena) < MINIMO_CONTRASENA:
        raise ContrasenaInvalida(
            f"La contraseña debe tener al menos {MINIMO_CONTRASENA} caracteres."
        )
    if len(contrasena) > MAXIMO_CONTRASENA:
        raise ContrasenaInvalida(f"La contraseña admite hasta {MAXIMO_CONTRASENA} caracteres.")
    if login and contrasena.strip().casefold() == normalizar_login(login):
        raise ContrasenaInvalida("La contraseña no puede ser igual al usuario.")
    if contrasena.strip().casefold() in CONTRASENAS_COMUNES:
        raise ContrasenaInvalida("Esa contraseña es demasiado común; elija otra.")


def _tomar_escritura(session: Session) -> None:
    """Toma el bloqueo de escritura de SQLite (`BEGIN IMMEDIATE`) ANTES de leer lo que se va a
    comprobar. pysqlite no abre transacción en un SELECT y el motor de `seguridad.base` no
    controla el `BEGIN`: sin esto, dos administradores que se desactivan a la vez leen ambos
    «queda otro» y confirman ambos, y no queda ninguno. El segundo espera (`busy_timeout`) hasta
    que el primero confirma y entonces ve su resultado. Si la sesión ya escribió, su
    transacción ya tiene el bloqueo y no se repite."""
    conexion = session.connection()
    if not conexion.connection.dbapi_connection.in_transaction:
        try:
            conexion.exec_driver_sql("BEGIN IMMEDIATE")
        except OperationalError as error:  # venció `busy_timeout`: otra escritura no termina
            session.rollback()
            raise ValueError(MENSAJE_BASE_OCUPADA) from error


def _huella(contrasena: str) -> str:
    with _semaforo:
        return _hasher.hash(contrasena)


@cache
def _huella_de_relleno() -> str:
    return _huella("relleno-para-igualar-el-tiempo-de-un-usuario-inexistente")


def _coincide(huella: str, contrasena: str) -> bool:
    with _semaforo:
        try:
            return _hasher.verify(huella, contrasena)
        except (VerificationError, InvalidHashError):
            return False


# --- ayudantes de estado --------------------------------------------------------------------


def _quien(usuario: Usuario | None) -> str:
    return "" if usuario is None else f"{usuario.nombre} <{usuario.login}>"


def texto_responsable(nombre: str, login: str, restablecida_por_admin: bool = False) -> str:
    """El responsable de un cambio: `Nombre <login>`, congelado en el momento (RF-82). Tras un
    restablecimiento del administrador y antes de que la persona cambie su contraseña se
    marca, para la trazabilidad (S3 §5.2, SEG-6). Cabe en `String(120)`."""
    marca = " (tras restablecimiento)" if restablecida_por_admin else ""
    base = f" <{login}>{marca}"
    return nombre[: 120 - len(base)] + base


def responsable_de(usuario: Usuario) -> str:
    return texto_responsable(usuario.nombre, usuario.login, usuario.restablecida_por_admin)


def _usuario(session: Session, usuario_id: int) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise LookupError(f"no hay una cuenta con id {usuario_id}")
    return usuario


def _exigir_administrador(actor: Usuario) -> None:
    if not actor.activo:
        raise PermisoDenegado("La cuenta que actúa está desactivada.")
    exigir(roles_de(actor.roles), Accion.ADMINISTRAR_CUENTAS)


def _intento(session: Session, clave: str) -> IntentoAcceso:
    fila = session.get(IntentoAcceso, clave)
    if fila is None:
        fila = IntentoAcceso(login_normalizado=clave, fallos_seguidos=0)
        session.add(fila)
        session.flush()
    return fila


def _fallar(session: Session, fila: IntentoAcceso, ahora: datetime, freno: FrenoGlobal) -> bool:
    """Cuenta un fallo; True si este fallo bloquea el login."""
    fila.fallos_seguidos += 1
    fila.ultimo_fallo = ahora
    freno.registrar_fallo(ahora)
    if fila.fallos_seguidos >= FALLOS_PARA_BLOQUEAR:
        fila.bloqueado_hasta = ahora + BLOQUEO
        return True
    return False


def clave_de_intento(login: str) -> str:
    """El login normalizado si puede ser un usuario (`PATRON_LOGIN`); si no, un marcador fijo.

    Lo que un anónimo teclea en el campo usuario se guarda en `evento_acceso` y se muestra al
    administrador: una contraseña pegada ahí quedaría legible. Una cuenta real siempre cumple el
    patrón (`validar_login`), así que el marcador nunca es el login de nadie: su contador y su
    bloqueo, compartidos por todo texto imposible, no pueden negarle el acceso a una persona
    real, y cada fallo sigue alimentando el freno global (`_fallar`).

    Limitación conocida: una contraseña que cumpla `PATRON_LOGIN` (3 a 40 caracteres de
    `[a-z0-9._-]`, sin espacios ni mayúsculas) se guarda como si fuera un login; no se distingue
    de uno. No se resuelve con un hash del marcador (decisión de la revisión)."""
    normal = normalizar_login(login)
    return normal if PATRON_LOGIN.fullmatch(normal) else LOGIN_NO_VALIDO


def _bloqueado(fila: IntentoAcceso, ahora: datetime) -> bool:
    """Bloqueado mientras `ahora < bloqueado_hasta`; al llegar la hora se libera y se reinicia."""
    if fila.bloqueado_hasta is None:
        return False
    if ahora < fila.bloqueado_hasta:
        return True
    fila.bloqueado_hasta, fila.fallos_seguidos = None, 0
    return False


# --- entrar ---------------------------------------------------------------------------------


def autenticar(
    session: Session,
    login: str,
    contrasena: str,
    ahora: datetime,
    *,
    ip: str = "",
    freno: FrenoGlobal | None = None,
    dormir: Dormir = time.sleep,
) -> Usuario:
    """El usuario si el par es correcto. `ErrorDeAcceso` (mismo mensaje exista o no el login) o
    `CuentaBloqueada`. Cuenta y registra el intento; confirma en todos los casos."""
    freno = FRENO if freno is None else freno
    espera = freno.espera(ahora)
    if espera:
        dormir(espera)
    clave = clave_de_intento(login)
    fila = _intento(session, clave)
    if _bloqueado(fila, ahora):
        eventos.registrar(session, "bloqueo", ahora, login=clave, ip=ip, detalle="login bloqueado")
        session.commit()
        raise CuentaBloqueada(MENSAJE_BLOQUEO)
    usuario = session.scalar(select(Usuario).where(Usuario.login == clave))
    existe = usuario is not None and usuario.activo
    huella = usuario.huella_clave if existe else _huella_de_relleno()
    correcta = _coincide(huella, contrasena)
    if existe and correcta:
        fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
        eventos.registrar(session, "entrada", ahora, login=clave, usuario_id=usuario.id, ip=ip)
        if _hace_falta_recalcular(usuario.huella_clave):
            usuario.huella_clave = _huella(contrasena)
        session.commit()
        return usuario
    bloquea = _fallar(session, fila, ahora, freno)
    eventos.registrar(session, "fallo", ahora, login=clave, ip=ip)
    if bloquea:
        eventos.registrar(session, "bloqueo", ahora, login=clave, ip=ip, detalle="5 fallos")
    session.commit()
    raise CuentaBloqueada(MENSAJE_BLOQUEO) if bloquea else ErrorDeAcceso(MENSAJE_FALLO)


def _hace_falta_recalcular(huella: str) -> bool:
    try:
        return _hasher.check_needs_rehash(huella)
    except InvalidHashError:
        return False


def purgar_intentos_de_inexistentes(session: Session, ahora: datetime) -> int:
    """Borra los contadores de logins que no existen y llevan 24 h sin fallar (S3 §5.4)."""
    existentes = set(session.scalars(select(Usuario.login)))
    viejos = [
        fila for fila in session.scalars(select(IntentoAcceso))
        if fila.login_normalizado not in existentes
        and not fila.login_normalizado.startswith("!")
        and fila.ultimo_fallo is not None
        and ahora - fila.ultimo_fallo >= PURGA_DE_INEXISTENTES
    ]
    for fila in viejos:
        session.delete(fila)
    session.commit()
    return len(viejos)


# --- primer administrador y código de instalación -------------------------------------------


def _huella_codigo(codigo: str) -> str:
    limpio = "".join(c for c in codigo.upper() if c.isalnum())
    return hashlib.sha256(limpio.encode("ascii", "ignore")).hexdigest()


def formato_codigo(codigo: str) -> str:
    return "-".join(codigo[i : i + 4] for i in range(0, len(codigo), 4))


def emitir_codigo(
    session: Session, carpeta: Path, ahora: datetime, *, motivo: str = "primera vez"
) -> str:
    """Un código de instalación de un solo uso: 20 caracteres base32 (100 bits) de `secrets`.
    Guarda su SHA-256 y lo escribe en `carpeta/codigo_instalacion.txt`. Toma el bloqueo de
    escritura, **invalida los códigos pendientes anteriores** (`usado` = `ahora`: solo el último
    sirve y el archivo siempre lleva el último) y confirma."""
    if motivo not in {"primera vez", "restablecimiento"}:
        raise ValueError("motivo de codigo desconocido")
    _tomar_escritura(session)
    reemplazados = session.execute(
        update(CodigoInstalacion).where(CodigoInstalacion.usado.is_(None)).values(usado=ahora)
    ).rowcount
    codigo = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LONGITUD_CODIGO))
    session.add(CodigoInstalacion(huella=_huella_codigo(codigo), creado=ahora, motivo=motivo))
    detalle = motivo if not reemplazados else f"{motivo}; reemplaza {reemplazados} pendiente(s)"
    eventos.registrar(session, "codigo de instalacion", ahora, detalle=detalle)
    session.commit()
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / NOMBRE_ARCHIVO_CODIGO).write_text(formato_codigo(codigo) + "\n", encoding="ascii")
    return codigo


def hay_usuarios(session: Session) -> bool:
    return bool(session.scalar(select(func.count()).select_from(Usuario)))


def preparar_primera_vez(session: Session, carpeta: Path, ahora: datetime) -> str | None:
    """Si no hay cuentas, asegura que haya un código vigente **y su archivo**: emite el de la
    primera vez si no hay ninguno vigente o si falta `codigo_instalacion.txt` (alguien lo borró y
    el código vigente quedó sin dueño: se invalida y se emite otro). Toma el bloqueo de escritura
    antes de mirar. Devuelve el código o `None` si no hacía falta."""
    _tomar_escritura(session)
    vigente = session.scalar(
        select(func.count()).select_from(CodigoInstalacion).where(CodigoInstalacion.usado.is_(None))
    )
    if hay_usuarios(session) or (vigente and (carpeta / NOMBRE_ARCHIVO_CODIGO).is_file()):
        session.rollback()  # no se escribió nada: se suelta el bloqueo
        return None
    return emitir_codigo(session, carpeta, ahora)


def _rechazar_codigo(session: Session, ahora: datetime, freno: FrenoGlobal, ip: str) -> None:
    """Un código inválido, usado, caducado o perdido en una carrera: cuenta el fallo (contador
    global del código y freno), lo registra sin el código y lanza el error de siempre."""
    fila = _intento(session, CLAVE_INTENTOS_CODIGO)
    bloquea = _fallar(session, fila, ahora, freno)
    eventos.registrar(session, "fallo", ahora, login="(codigo)", ip=ip, detalle="codigo")
    session.commit()
    raise CuentaBloqueada(MENSAJE_BLOQUEO) if bloquea else ErrorDeAcceso(MENSAJE_CODIGO)


def reclamar_instalacion(
    session: Session,
    codigo: str,
    login: str,
    nombre: str,
    contrasena: str,
    ahora: datetime,
    carpeta: Path,
    *,
    ip: str = "",
    freno: FrenoGlobal | None = None,
    dormir: Dormir = time.sleep,
    ademas_arma: bool = False,
) -> Usuario:
    """Crea el primer administrador (o, con un código de restablecimiento, devuelve el acceso a
    un administrador). El código solo se acepta mientras no haya cuentas o haya un
    restablecimiento pendiente (y este, menos de 24 h), con el mismo freno que el acceso; al
    usarse se borra el archivo y se invalida la huella.

    Dos reclamos del mismo código nunca crean dos cuentas: el bloqueo de escritura se toma
    antes de leer y el uso del código es un `UPDATE ... WHERE usado IS NULL` que debe afectar
    una fila. `ademas_arma` da también el rol de armar a la cuenta NUEVA (no cambia nada más en
    un restablecimiento). `ValueError(MENSAJE_BASE_OCUPADA)` si otra escritura no termina."""
    freno = FRENO if freno is None else freno
    espera = freno.espera(ahora)
    if espera:
        dormir(espera)
    # Bloqueo de escritura ANTES de leer si el código sigue vivo y si hay cuentas: dos reclamos
    # simultáneos del mismo código se serializan (el segundo espera y ve `usado` fijado).
    _tomar_escritura(session)
    fila = _intento(session, CLAVE_INTENTOS_CODIGO)
    if _bloqueado(fila, ahora):
        session.commit()
        raise CuentaBloqueada(MENSAJE_BLOQUEO)
    pendiente = session.get(CodigoInstalacion, _huella_codigo(codigo))
    vigente = pendiente is not None and pendiente.usado is None
    caducado = (
        vigente
        and pendiente.motivo == "restablecimiento"
        and ahora - pendiente.creado >= CADUCIDAD_RESTABLECIMIENTO
    )
    aceptable = (
        vigente and not caducado
        and (not hay_usuarios(session) or pendiente.motivo == "restablecimiento")
    )
    if not aceptable:
        _rechazar_codigo(session, ahora, freno, ip)
    try:
        login_normal = validar_login(login)
        validar_contrasena(contrasena, login_normal)
    except ValueError:
        session.rollback()  # la forma estaba mal: no se gasta el código y se suelta el bloqueo
        raise
    huella = _huella(contrasena)
    # Defensa extra: el uso del código es atómico. Si otra transacción lo gastó entre la lectura
    # y aquí (el bloqueo de arriba no debería permitirlo), se rechaza como un código usado.
    gastado = session.execute(
        update(CodigoInstalacion)
        .where(CodigoInstalacion.huella == pendiente.huella, CodigoInstalacion.usado.is_(None))
        .values(usado=ahora)
    )
    if gastado.rowcount != 1:
        session.rollback()
        _rechazar_codigo(session, ahora, freno, ip)
    motivo = pendiente.motivo
    usuario = session.scalar(select(Usuario).where(Usuario.login == login_normal))
    if usuario is None:
        roles = [Rol.ADMINISTRADOR, *([Rol.ARMA] if ademas_arma else [])]
        usuario = Usuario(
            login=login_normal, nombre=nombre.strip() or login_normal, huella_clave=huella,
            roles=texto_de_roles(roles), activo=True, debe_cambiar_clave=False,
            restablecida_por_admin=False, creado=ahora, creado_por="código de instalación",
        )
        session.add(usuario)
        session.flush()
    else:  # restablecimiento: el administrador recupera su cuenta
        eran = roles_de(usuario.roles)
        usuario.huella_clave, usuario.activo = huella, True
        usuario.roles = texto_de_roles({*eran, Rol.ADMINISTRADOR})
        usuario.debe_cambiar_clave = False
        sesiones.cerrar_todas(session, usuario.id, "restablecimiento")
        if Rol.ADMINISTRADOR not in eran:
            eventos.registrar(
                session, "cambio de roles", ahora, login=login_normal, usuario_id=usuario.id,
                ip=ip, detalle=f"{usuario.roles}; promovida a administrador por restablecimiento",
            )
    fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
    eventos.registrar(
        session, "alta", ahora, login=login_normal, usuario_id=usuario.id, ip=ip,
        detalle=f"administrador por {motivo}",
    )
    session.commit()
    (carpeta / NOMBRE_ARCHIVO_CODIGO).unlink(missing_ok=True)
    return usuario


def emitir_codigo_de_restablecimiento(session: Session, carpeta: Path, ahora: datetime) -> str:
    """`python -m operacion restablecer-administrador` (exige acceso al equipo): un código nuevo
    (caduca a las 24 h; invalida los pendientes) y cierra las sesiones de los administradores
    (S3 §5.4)."""
    _tomar_escritura(session)
    for usuario in session.scalars(select(Usuario)):
        if Rol.ADMINISTRADOR in roles_de(usuario.roles):
            sesiones.cerrar_todas(session, usuario.id, "restablecimiento")
    return emitir_codigo(session, carpeta, ahora, motivo="restablecimiento")


# --- administrar cuentas --------------------------------------------------------------------


def crear_usuario(
    session: Session,
    actor: Usuario,
    login: str,
    nombre: str,
    roles: Iterable[Rol | str],
    contrasena_temporal: str,
    ahora: datetime,
) -> Usuario:
    """Alta por el administrador, con contraseña temporal que obliga a cambiarla al entrar."""
    _exigir_administrador(actor)
    login_normal = validar_login(login)
    validar_contrasena(contrasena_temporal, login_normal)
    if session.scalar(select(Usuario.id).where(Usuario.login == login_normal)) is not None:
        raise ValueError(f"Ya existe una cuenta con el usuario {login_normal!r}.")
    usuario = Usuario(
        login=login_normal, nombre=nombre.strip() or login_normal,
        huella_clave=_huella(contrasena_temporal), roles=texto_de_roles(roles), activo=True,
        debe_cambiar_clave=True, restablecida_por_admin=False, creado=ahora,
        creado_por=_quien(actor),
    )
    session.add(usuario)
    session.flush()
    eventos.registrar(
        session, "alta", ahora, login=login_normal, usuario_id=usuario.id,
        detalle=f"roles {usuario.roles}; por {actor.login}",
    )
    session.commit()
    return usuario


def cambiar_roles(
    session: Session, actor: Usuario, usuario_id: int, roles: Iterable[Rol | str], ahora: datetime
) -> Usuario:
    _tomar_escritura(session)
    session.refresh(actor)  # puede haber sido desactivado mientras tanto
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    session.refresh(usuario)
    nuevos = texto_de_roles(roles)
    if Rol.ADMINISTRADOR in roles_de(usuario.roles) and Rol.ADMINISTRADOR not in roles_de(nuevos):
        _exigir_otro_administrador(session, usuario)
    usuario.roles = nuevos
    sesiones.cerrar_todas(session, usuario.id, "cambio de roles")
    eventos.registrar(
        session, "cambio de roles", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"{nuevos}; por {actor.login}",
    )
    session.commit()
    return usuario


def _exigir_otro_administrador(session: Session, usuario: Usuario) -> None:
    otros = [
        u for u in session.scalars(
            select(Usuario).where(Usuario.activo.is_(True)).execution_options(populate_existing=True)
        )
        if u.id != usuario.id and Rol.ADMINISTRADOR in roles_de(u.roles)
    ]
    if not otros:
        raise ValueError("Debe quedar al menos un administrador activo.")


def desactivar(session: Session, actor: Usuario, usuario_id: int, ahora: datetime) -> None:
    """Las cuentas no se borran: se desactivan, para que sus registros sigan teniendo dueño."""
    _tomar_escritura(session)
    session.refresh(actor)  # puede haber sido desactivado mientras tanto
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    session.refresh(usuario)
    if Rol.ADMINISTRADOR in roles_de(usuario.roles):
        _exigir_otro_administrador(session, usuario)
    usuario.activo = False
    sesiones.cerrar_todas(session, usuario.id, "cuenta desactivada")
    eventos.registrar(
        session, "baja", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"por {actor.login}",
    )
    session.commit()


def reactivar(session: Session, actor: Usuario, usuario_id: int, ahora: datetime) -> None:
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    usuario.activo = True
    eventos.registrar(
        session, "alta", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"reactivada por {actor.login}",
    )
    session.commit()


def desbloquear(session: Session, actor: Usuario, login: str, ahora: datetime) -> None:
    _exigir_administrador(actor)
    clave = normalizar_login(login)
    fila = session.get(IntentoAcceso, clave)
    if fila is not None:
        fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
    eventos.registrar(session, "desbloqueo", ahora, login=clave, detalle=f"por {actor.login}")
    session.commit()


def restablecer(
    session: Session, actor: Usuario, usuario_id: int, contrasena_temporal: str, ahora: datetime
) -> None:
    """Contraseña temporal nueva: obliga a cambiarla, cierra las sesiones de la cuenta y marca
    sus cambios siguientes en la trazabilidad hasta que la persona la cambie."""
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    validar_contrasena(contrasena_temporal, usuario.login)
    usuario.huella_clave = _huella(contrasena_temporal)
    usuario.debe_cambiar_clave, usuario.restablecida_por_admin = True, True
    fila = session.get(IntentoAcceso, usuario.login)
    if fila is not None:
        fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
    sesiones.cerrar_todas(session, usuario.id, "restablecimiento")
    eventos.registrar(
        session, "restablecimiento", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"por {actor.login}",
    )
    session.commit()


def cambiar_contrasena(
    session: Session, usuario_id: int, actual: str, nueva: str, ahora: datetime
) -> str:
    """Cambia la contraseña propia: cierra todas las fichas y devuelve una NUEVA (S3 §5.3)."""
    usuario = _usuario(session, usuario_id)
    if not _coincide(usuario.huella_clave, actual):
        raise ErrorDeAcceso(MENSAJE_FALLO)
    validar_contrasena(nueva, usuario.login)
    usuario.huella_clave = _huella(nueva)
    usuario.debe_cambiar_clave, usuario.restablecida_por_admin = False, False
    sesiones.cerrar_todas(session, usuario.id, "cambio de clave")
    eventos.registrar(
        session, "cambio de clave", ahora, login=usuario.login, usuario_id=usuario.id
    )
    session.commit()
    return sesiones.abrir(session, usuario, ahora)
