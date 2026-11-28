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

Decisiones y endurecimiento de la revisión de seguridad de C9a:

- El tope «5 por equipo cada hora» se aplica primero en memoria (`CUPO`, al estilo de `FRENO` pero
  por equipo) ANTES de Argon2, para que una ráfaga concurrente no pague 64 MiB por intento, y se
  verifica también contra los eventos `solicitud` y `solicitud fallida` en la base (`_exigir_cupo`).
  En ambos se agrupa IPv6 por su prefijo `/64` (y las IPv4 mapeadas en IPv6 con su IPv4). Las 50
  pendientes se cuentan en `solicitud_cuenta`.
- El login es único en `solicitud_cuenta`: una solicitud rechazada o vencida no retiene su login;
  pedirlo de nuevo reutiliza la fila (que vuelve a empezar como pendiente), deja en el evento
  `solicitud` el detalle «reutiliza una solicitud <estado> resuelta por <quién>» y `listar` marca
  `reutilizada=True` para que la interfaz avise al administrador.
- Una aprobación guarda `resuelta_por_id` (FK a `usuario.id`) y no sobrevive a quien la dio: al
  canjear se exige que esa cuenta siga activa y administradora; si no, se rechaza con el mismo
  mensaje genérico y el detalle `aprobador revocado`.
- `listar` es de solo lectura: calcula `vencida` al responder sin escribir en la base; el paso a
  `vencida` se persiste en `aprobar`, `canjear` y `solicitar`.
- El motivo de un canje rechazado (`sin solicitud`, `solicitud <estado>`, `codigo vencido`,
  `aprobador revocado`, `codigo`, `contrasena`) queda en el detalle del evento, que solo ve el
  administrador; a la persona siempre se le dice lo mismo. Nunca el código ni la contraseña.
"""

from __future__ import annotations

import hmac
import ipaddress
import re
import threading
import time
import unicodedata
from collections import deque
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
from seguridad.permisos import Accion, Rol, permitido, roles_de, texto_de_roles
from seguridad.retencion import estado_efectivo, por_login, vigente, viva

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
#: Prefijo del detalle en `evento_acceso` cuando una solicitud reutiliza una rechazada o vencida.
PREFIJO_REUTILIZADA = "reutiliza una solicitud"
_MAXIMO_CLAVES_EN_MEMORIA = 256

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


@dataclass(frozen=True, slots=True)
class SolicitudListada:
    """Vista de solo lectura de una solicitud: `estado` calcula `vencida` al responder sin
    escribir en la base, y `reutilizada` indica si ese usuario ya se pidió antes."""

    id: int
    nombre: str
    login: str
    correo: str
    creada: datetime
    estado: str
    papel: str | None
    vence: datetime | None
    reutilizada: bool


def clave_de_equipo(ip: str) -> str:
    """Clave de cupo para una dirección de cliente: la IPv4 tal cual (también si viene mapeada en
    IPv6 como `::ffff:...`), el prefijo `/64` en IPv6 (un mismo equipo puede rotar su sufijo
    dentro del `/64`), o el texto recortado si no es una dirección IP válida."""
    texto = ip.strip()
    if not texto:
        return ""
    sin_zona = texto.split("%", 1)[0]
    try:
        direccion = ipaddress.ip_address(sin_zona)
    except ValueError:
        return texto
    if isinstance(direccion, ipaddress.IPv6Address):
        if direccion.ipv4_mapped is not None:
            return str(direccion.ipv4_mapped)
        return str(ipaddress.IPv6Network((direccion, 64), strict=False))
    return str(direccion)


class CupoPorEquipo:
    """Contador en memoria de intentos de solicitud por equipo (por `/64` en IPv6), al estilo de
    `FrenoGlobal`: se toma y suma ANTES de Argon2 para que una ráfaga no pague 64 MiB por intento.
    Estado del proceso (excepción declarada de S3 §4.4, igual que `FRENO`)."""

    def __init__(
        self,
        maximo: int = MAXIMO_POR_EQUIPO,
        ventana: timedelta = VENTANA_POR_EQUIPO,
    ) -> None:
        self._maximo = maximo
        self._ventana = ventana
        self._intentos: dict[str, deque[datetime]] = {}
        self._candado = threading.Lock()

    def tomar(self, ip: str, ahora: datetime) -> bool:
        """Consume un intento del equipo si está bajo el tope (`True`); si ya llegó al límite en
        la última hora, no suma nada y devuelve `False`."""
        clave = clave_de_equipo(ip)
        with self._candado:
            cola = self._intentos.get(clave)
            if cola is not None:
                self._podar(cola, ahora)
                if not cola:
                    del self._intentos[clave]
                    cola = None
            if cola is not None and len(cola) >= self._maximo:
                return False
            if cola is None:
                cola = deque()
                self._intentos[clave] = cola
            cola.append(ahora)
            if len(self._intentos) > _MAXIMO_CLAVES_EN_MEMORIA:
                self._limpiar_vacias(ahora)
            return True

    def reiniciar(self) -> None:
        with self._candado:
            self._intentos.clear()

    def _podar(self, cola: deque[datetime], ahora: datetime) -> None:
        while cola and ahora - cola[0] >= self._ventana:
            cola.popleft()

    def _limpiar_vacias(self, ahora: datetime) -> None:
        vacias = []
        for clave, cola in self._intentos.items():
            self._podar(cola, ahora)
            if not cola:
                vacias.append(clave)
        for clave in vacias:
            del self._intentos[clave]


CUPO = CupoPorEquipo()


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
    guardadas y las que dieron 409; los de hace una hora exacta ya no cuentan; IPv6 agrupado por
    `/64`) o con 50 pendientes en total."""
    objetivo = clave_de_equipo(ip)
    recientes = session.scalars(
        select(EventoAcceso.ip_cliente).where(
            EventoAcceso.tipo.in_(TIPOS_DEL_CUPO),
            EventoAcceso.fecha_hora > ahora - VENTANA_POR_EQUIPO,
        )
    )
    del_equipo = sum(1 for registrada in recientes if clave_de_equipo(registrada) == objetivo)
    pendientes = session.scalar(
        select(func.count())
        .select_from(SolicitudCuenta)
        .where(SolicitudCuenta.estado == "pendiente")
    )
    if del_equipo >= MAXIMO_POR_EQUIPO or pendientes >= MAXIMO_PENDIENTES:
        raise DemasiadasSolicitudes(MENSAJE_LIMITE)


def _persistir_vencidas(session: Session, ahora: datetime) -> None:
    """Pasa a `vencida` en la base toda aprobada cuyo código ya venció (`vence` ≤ `ahora`)."""
    vencidas = session.scalars(
        select(SolicitudCuenta)
        .where(
            SolicitudCuenta.estado == "aprobada",
            SolicitudCuenta.vence.is_not(None),
            SolicitudCuenta.vence <= ahora,
        )
        .execution_options(populate_existing=True)
    )
    for solicitud in vencidas:
        solicitud.estado = "vencida"


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
    cupo: CupoPorEquipo | None = None,
) -> SolicitudCuenta:
    """Guarda una solicitud pendiente (no una cuenta). Valida con las reglas de siempre
    (`validar_login`, `validar_contrasena`), el nombre y la forma del correo (`ValueError`);
    `DemasiadasSolicitudes` pasado el tope y `LoginEnUso` si el login ya es de alguien. El cupo en
    memoria se toma y suma ANTES de Argon2 (y se verifica en la base antes y con el bloqueo de
    escritura tomado). Reutilizar una rechazada o vencida anota en el evento `solicitud` qué fila
    reutiliza y quién la resolvió."""
    cupo = CUPO if cupo is None else cupo
    login_normal = validar_login(login)
    validar_contrasena(contrasena, login_normal)
    nombre_limpio = validar_nombre(nombre)
    correo_limpio = validar_correo(correo)
    if not cupo.tomar(ip, ahora):
        raise DemasiadasSolicitudes(MENSAJE_LIMITE)
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
    detalle = ""
    if solicitud is None:
        solicitud = SolicitudCuenta(login=login_normal)
        session.add(solicitud)
    else:
        estado_previo = estado_efectivo(solicitud, ahora)
        quien = solicitud.resuelta_por or "desconocido"
        detalle = f"{PREFIJO_REUTILIZADA} {estado_previo} resuelta por {quien}"
    solicitud.nombre, solicitud.correo = nombre_limpio, correo_limpio
    solicitud.huella_clave = huella
    solicitud.creada, solicitud.estado, solicitud.resuelta_por = ahora, "pendiente", ""
    solicitud.resuelta_por_id = None
    solicitud.papel = solicitud.huella_codigo = solicitud.vence = None
    _persistir_vencidas(session, ahora)
    eventos.registrar(session, "solicitud", ahora, login=login_normal, ip=ip, detalle=detalle)
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


def _logins_reutilizados(session: Session) -> set[str]:
    """Los logins cuya solicitud reutilizó una fila rechazada o vencida."""
    return set(
        session.scalars(
            select(EventoAcceso.login_intentado)
            .where(
                EventoAcceso.tipo == "solicitud",
                EventoAcceso.detalle.like(f"{PREFIJO_REUTILIZADA}%"),
            )
            .distinct()
        )
    )


def listar(session: Session, actor: Usuario, ahora: datetime) -> list[SolicitudListada]:
    """Todas las solicitudes, las más nuevas primero. Solo lectura (no toma bloqueo de escritura
    ni escribe en la base): una aprobada cuyo código ya venció (`vence` ≤ `ahora`) sale como
    `vencida` al responder; el cambio se persiste en `aprobar`, `canjear` y `solicitar`. Solo el
    administrador (`PermisoDenegado`)."""
    session.refresh(actor)
    _exigir_administrador(actor)
    reutilizadas = _logins_reutilizados(session)
    filas = session.scalars(
        select(SolicitudCuenta).order_by(SolicitudCuenta.creada.desc(), SolicitudCuenta.id.desc())
    )
    return [
        SolicitudListada(
            id=solicitud.id,
            nombre=solicitud.nombre,
            login=solicitud.login,
            correo=solicitud.correo,
            creada=solicitud.creada,
            estado=estado_efectivo(solicitud, ahora),
            papel=solicitud.papel,
            vence=solicitud.vence,
            reutilizada=solicitud.login in reutilizadas,
        )
        for solicitud in filas
    ]


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
    solicitud.resuelta_por_id = actor.id
    _persistir_vencidas(session, ahora)
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
    solicitud.resuelta_por_id = actor.id
    eventos.registrar(
        session, "solicitud rechazada", ahora, login=solicitud.login, detalle=f"por {actor.login}"
    )
    session.commit()
    return solicitud


# --- canjear el código ----------------------------------------------------------------------


def _aprobador_vigente(session: Session, solicitud: SolicitudCuenta) -> bool:
    """True si quien aprobó sigue existiendo, activo y con permiso de administrar cuentas."""
    if solicitud.resuelta_por_id is None:
        return False
    aprobador = session.get(Usuario, solicitud.resuelta_por_id, populate_existing=True)
    return (
        aprobador is not None
        and aprobador.activo
        and permitido(roles_de(aprobador.roles), Accion.ADMINISTRAR_CUENTAS)
    )


def _motivo_sin_contrasena(
    session: Session, solicitud: SolicitudCuenta | None, codigo: str, ahora: datetime
) -> str | None:
    """Lo que se exige antes de la contraseña, en este orden: estado `aprobada`, `vence` > ahora,
    aprobador activo y administrador, y la huella del código. `None` si todo eso vale."""
    if solicitud is None:
        return "sin solicitud"
    if solicitud.estado != "aprobada":
        return f"solicitud {solicitud.estado}"
    if not vigente(solicitud, ahora):
        return "codigo vencido"
    if not _aprobador_vigente(session, solicitud):
        return "aprobador revocado"
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
    este orden, estado `aprobada`, `vence` > ahora, aprobador aún activo y administrador, la huella
    del código y la contraseña (Argon2, que solo corre si lo anterior vale). Cualquier fallo da
    `ErrorDeAcceso(MENSAJE_CANJE)` y cuenta en el contador del login y en el freno, como
    `cuentas.autenticar`; el quinto seguido bloquea (`CuentaBloqueada`). Confirma en todos los
    casos y persiste las solicitudes aprobadas que ya vencieron."""
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
    pasa = not bloqueado_antes and _motivo_sin_contrasena(session, previa, codigo, ahora) is None
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
    motivo = _motivo_sin_contrasena(session, solicitud, codigo, ahora)
    if motivo is None and not (correcta and solicitud.huella_clave == huella):
        motivo = "contrasena"
    existe = session.scalar(select(Usuario.id).where(Usuario.login == clave)) is not None
    if motivo is None and existe:
        motivo = "la cuenta ya existe"
    if motivo is not None:
        bloquea = _fallar(session, fila, ahora, freno)
        _persistir_vencidas(session, ahora)
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
    _persistir_vencidas(session, ahora)
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
