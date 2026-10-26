"""Envíos, dictámenes y rastro encadenado de las aprobaciones (MP-4, Tarea 17; diseño de montar un
presupuesto §5.4 y §10).

Máquina de estados de una versión guardada: guardada → en aprobación → aprobada | aprobada con
observaciones | devuelta; y retirada, cuando se envía otra versión de la misma obra (**un solo envío
pendiente por obra**). La devuelta no se reenvía tal cual: se corrige en una versión nueva. Quien
armó la versión (el usuario de su eslabón, decisión 7 ratificada) también puede dictaminar, y el
evento queda con `armo` verdadero para rotularlo «aprobada por quien la armó». Quién puede enviar o
dictaminar lo decide la API (`editar_hoja`, `aprobar_version`), no este módulo.

**Rastro.** Cada envío, retiro y dictamen es una fila nueva de `mp_aprobacion_evento` (solo
inserción) con el sello del eslabón de su versión (`EslabonVersion.huella_eslabon`) y su propia
huella, encadenada a la anterior de la misma obra desde `GENESIS`:

    huella = SHA-256(json.dumps({anterior, tipo, proyecto_id, version, huella_version, resultado,
                                 notas, usuario, fecha_hora (isoformat), armo, cierre_de},
                                sort_keys=True, separators=(",", ":"), ensure_ascii=False))

`verificar_rastro` recalcula cada huella y su encadenamiento y compara el sello guardado con el
eslabón actual de la versión. Borrar el último evento no se detecta (límite de toda cadena sin
ancla externa, igual que la del núcleo).

**Todo o nada.** `enviar` y `dictaminar` confirman (`commit`) sus filas juntas o ninguna. La
concurrencia la guarda la base: `cierre_de` único (un envío se cierra una vez) y (`proyecto_id`,
`anterior`) único (dos eventos no cuelgan del mismo eslabón). Si otra sesión escribió entre la
lectura y la escritura (`IntegrityError`, o en SQLite WAL el `database is locked` de una lectura que
quedó vieja), se deshace, se relee y se valida otra vez: el segundo dictamen recibe «Este envío ya
tiene dictamen o fue retirado.» y no queda rastro doble.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from aplicacion.proyectos import resolver_proyecto
from aplicacion.revision import login_de
from aplicacion.tablas_aprobacion import FilaEventoAprobacion
from core import models
from core.budget.cadena import GENESIS
from core.models.cadena import EslabonVersion

__all__ = [
    "APROBADAS",
    "ESTADOS",
    "RESULTADOS",
    "AprobacionInvalida",
    "Envio",
    "EstadoDeVersion",
    "EventoAprobacion",
    "RastroVerificado",
    "dictaminar",
    "enviar",
    "estados",
    "fases",
    "historial",
    "ultima_aprobada",
    "verificar_rastro",
]

ESTADOS = (
    "guardada",
    "en_aprobacion",
    "retirada",
    "aprobada",
    "aprobada_con_observaciones",
    "devuelta",
)
RESULTADOS = ("aprobada", "aprobada_con_observaciones", "devuelta")
APROBADAS = ("aprobada", "aprobada_con_observaciones")
_CON_NOTAS_OBLIGATORIAS = ("devuelta", "aprobada_con_observaciones")
_LARGO_DE_NOTAS = 2000

#: Cómo se lee cada estado en las fases de una obra («VIV-001 devuelta → VIV-002 aprobada»).
_EN_LAS_FASES = {
    "en_aprobacion": "en aprobación",
    "retirada": "retirada",
    "aprobada": "aprobada",
    "aprobada_con_observaciones": "aprobada con observaciones",
    "devuelta": "devuelta",
}

SIN_NOTAS = "Escriba las notas: son obligatorias para devolver o aprobar con observaciones."
CERRADO = "Este envío ya tiene dictamen o fue retirado."
SIN_ENVIO = "No se encontró ese envío."
DICTAMEN_DESCONOCIDO = "Elija el dictamen: aprobada, aprobada con observaciones o devuelta."
NOTAS_LARGAS = f"Las notas no pueden pasar de {_LARGO_DE_NOTAS} caracteres."
INTEGRO = "Rastro de aprobaciones íntegro."
CHOQUE = (
    "Otra persona registró un movimiento de aprobación de esta obra al mismo tiempo: "
    "vuelva a intentarlo."
)


class AprobacionInvalida(ValueError):  # noqa: N818
    """Lo que la regla no permite; la API lo devuelve como 409 o 422 con este mismo mensaje."""


@dataclass(frozen=True, slots=True)
class Envio:
    id: int
    retirada: str | None  # la versión que estaba pendiente y este envío retiró


@dataclass(frozen=True, slots=True)
class EstadoDeVersion:
    estado: str  # uno de ESTADOS
    por: str | None  # quién hizo el último movimiento (None si solo está guardada)
    el: datetime | None
    notas: str
    armo: bool  # quien hizo el último movimiento es quien guardó la versión


@dataclass(frozen=True, slots=True)
class EventoAprobacion:
    id: int
    proyecto_id: int
    tipo: str  # envio | retiro | dictamen
    version: str
    huella_version: str
    resultado: str | None
    notas: str
    usuario: str
    fecha_hora: datetime
    armo: bool
    cierre_de: int | None
    anterior: str
    huella: str


@dataclass(frozen=True, slots=True)
class RastroVerificado:
    integro: bool
    mensaje: str


# --- escrituras ---------------------------------------------------------------------------------


def enviar(
    sesion: Session, proyecto: str, version: str, *, nota: str, usuario: str, ahora: datetime
) -> Envio:
    """Envía `version` a aprobación. Si la obra tenía otro envío pendiente, lo retira en la misma
    transacción y `Envio.retirada` lo nombra. Confirma; `AprobacionInvalida` si no se puede."""

    def operacion() -> Envio:
        obra = _obra(sesion, proyecto)
        presupuesto = _version(sesion, obra, version)
        sello = _sello(sesion, presupuesto)
        nota_limpia = _notas_validas(nota)
        eventos = _eventos(sesion, obra.id)
        estado = _estados_por_version(eventos).get(version)
        if estado is not None:
            _exigir_que_se_pueda_enviar(version, estado.estado)
        pendiente = _pendiente(eventos)
        anterior = _cabeza(sesion, obra.id)
        retirada = None
        if pendiente is not None:
            otra = _version(sesion, obra, pendiente.version)
            retiro = _insertar(
                sesion,
                anterior=anterior,
                proyecto_id=obra.id,
                tipo="retiro",
                version=pendiente.version,
                huella_version=_sello(sesion, otra),
                resultado=None,
                notas="",
                usuario=usuario,
                fecha_hora=ahora,
                armo=_armo(usuario, _quien_guardo(sesion, otra)),
                cierre_de=pendiente.id,
            )
            anterior, retirada = retiro.huella, pendiente.version
        fila = _insertar(
            sesion,
            anterior=anterior,
            proyecto_id=obra.id,
            tipo="envio",
            version=version,
            huella_version=sello,
            resultado=None,
            notas=nota_limpia,
            usuario=usuario,
            fecha_hora=ahora,
            armo=_armo(usuario, _quien_guardo(sesion, presupuesto)),
            cierre_de=None,
        )
        return Envio(fila.id, retirada)

    return _escribir(sesion, operacion)


def dictaminar(
    sesion: Session, envio_id: int, *, resultado: str, notas: str, usuario: str, ahora: datetime
) -> int:
    """Registra el dictamen sobre el envío `envio_id` y devuelve el id del evento. Notas
    obligatorias para devolver y para aprobar con observaciones. Confirma; `AprobacionInvalida`
    si el envío no existe, ya está cerrado o el dictamen no es válido."""

    def operacion() -> int:
        envio = sesion.get(FilaEventoAprobacion, envio_id, populate_existing=True)
        if envio is None or envio.tipo != "envio":
            raise AprobacionInvalida(SIN_ENVIO)
        cerrado = sesion.scalar(
            select(FilaEventoAprobacion.id).where(FilaEventoAprobacion.cierre_de == envio_id)
        )
        if cerrado is not None:
            raise AprobacionInvalida(CERRADO)
        if resultado not in RESULTADOS:
            raise AprobacionInvalida(DICTAMEN_DESCONOCIDO)
        notas_limpias = _notas_validas(notas)
        if resultado in _CON_NOTAS_OBLIGATORIAS and not notas_limpias:
            raise AprobacionInvalida(SIN_NOTAS)
        obra = sesion.get(models.Proyecto, envio.proyecto_id)
        if obra is None:  # la obra se borró después del envío: no hay a qué atar el dictamen
            raise AprobacionInvalida(SIN_ENVIO)
        presupuesto = _version(sesion, obra, envio.version)
        fila = _insertar(
            sesion,
            anterior=_cabeza(sesion, obra.id),
            proyecto_id=obra.id,
            tipo="dictamen",
            version=envio.version,
            huella_version=_sello(sesion, presupuesto),
            resultado=resultado,
            notas=notas_limpias,
            usuario=usuario,
            fecha_hora=ahora,
            armo=_armo(usuario, _quien_guardo(sesion, presupuesto)),
            cierre_de=envio_id,
        )
        return fila.id

    return _escribir(sesion, operacion)


# --- lecturas -----------------------------------------------------------------------------------


def estados(sesion: Session, proyecto: str) -> dict[str, EstadoDeVersion]:
    """El estado de cada versión guardada de la obra, en el orden en que se guardaron."""
    obra = _obra(sesion, proyecto)
    por_version = _estados_por_version(_eventos(sesion, obra.id))
    guardada = EstadoDeVersion("guardada", None, None, "", False)
    return {
        codigo: por_version.get(codigo, guardada)
        for codigo in sesion.scalars(
            select(models.Presupuesto.codigo)
            .where(models.Presupuesto.proyecto_id == obra.id)
            .order_by(models.Presupuesto.id)
        )
    }


def historial(sesion: Session, proyecto: str) -> list[EventoAprobacion]:
    """Todos los eventos de la obra, en el orden del rastro."""
    return _eventos(sesion, _obra(sesion, proyecto).id)


def fases(sesion: Session, proyecto: str) -> str:
    """Cada envío de la obra con su desenlace, encadenados: «VIV-001 devuelta → VIV-002
    aprobada». Vacío si la obra no tiene envíos."""
    eventos = _eventos(sesion, _obra(sesion, proyecto).id)
    cierres = {e.cierre_de: e for e in eventos if e.cierre_de is not None}
    partes = []
    for envio in (e for e in eventos if e.tipo == "envio"):
        cierre = cierres.get(envio.id)
        estado = _estado_del_evento(cierre) if cierre is not None else "en_aprobacion"
        partes.append(f"{envio.version} {_EN_LAS_FASES[estado]}")
    return " → ".join(partes)


def ultima_aprobada(sesion: Session, proyecto: str) -> str | None:
    """La versión del último dictamen que aprobó (con o sin observaciones), o `None`."""
    aprobadas = [
        e.version
        for e in _eventos(sesion, _obra(sesion, proyecto).id)
        if e.tipo == "dictamen" and e.resultado in APROBADAS
    ]
    return aprobadas[-1] if aprobadas else None


def verificar_rastro(sesion: Session, proyecto: str) -> RastroVerificado:
    """RECALCULA cada huella, su encadenamiento desde `GENESIS` y el sello de cada versión contra
    su eslabón actual; dice el primer evento donde se rompe."""
    obra = _obra(sesion, proyecto)
    sellos = {
        codigo: huella
        for codigo, huella in sesion.execute(
            select(models.Presupuesto.codigo, EslabonVersion.huella_eslabon)
            .join(EslabonVersion, EslabonVersion.presupuesto_id == models.Presupuesto.id)
            .where(models.Presupuesto.proyecto_id == obra.id)
        )
    }
    anterior = GENESIS
    for evento in _eventos(sesion, obra.id):
        if (
            evento.anterior != anterior
            or evento.huella != _huella_del_evento(evento)
            or sellos.get(evento.version) != evento.huella_version
        ):
            return RastroVerificado(
                False, f"El rastro de aprobaciones se rompió en el evento n.º {evento.id}."
            )
        anterior = evento.huella
    return RastroVerificado(True, INTEGRO)


# --- ayudantes ----------------------------------------------------------------------------------


class _ChoqueDeEscritura(Exception):  # noqa: N818
    """Otra sesión escribió entre la lectura y la escritura de esta."""


def _escribir[T](sesion: Session, operacion: Callable[[], T]) -> T:
    """Corre `operacion` y confirma, todo o nada. Ante un choque con otra sesión, deshace y lo
    intenta una vez más desde una lectura nueva (que normalmente rechaza con el mensaje de la
    regla); si vuelve a chocar, `AprobacionInvalida(CHOQUE)`."""
    try:
        return _confirmar(sesion, operacion)
    except _ChoqueDeEscritura:
        pass
    try:
        return _confirmar(sesion, operacion)
    except _ChoqueDeEscritura as choque:
        raise AprobacionInvalida(CHOQUE) from choque


def _confirmar[T](sesion: Session, operacion: Callable[[], T]) -> T:
    try:
        resultado = operacion()
        sesion.commit()
    except (IntegrityError, OperationalError) as error:
        sesion.rollback()
        if isinstance(error, OperationalError) and "locked" not in str(error.orig).lower():
            raise
        raise _ChoqueDeEscritura from error
    except BaseException:
        sesion.rollback()
        raise
    return resultado


def _cabeza(sesion: Session, proyecto_id: int) -> str:
    """La huella del último evento de la obra (`GENESIS` si no hay)."""
    ultima = sesion.scalar(
        select(FilaEventoAprobacion.huella)
        .where(FilaEventoAprobacion.proyecto_id == proyecto_id)
        .order_by(FilaEventoAprobacion.id.desc())
        .limit(1)
    )
    return GENESIS if ultima is None else ultima


def _huella(
    *,
    anterior: str,
    tipo: str,
    proyecto_id: int,
    version: str,
    huella_version: str,
    resultado: str | None,
    notas: str,
    usuario: str,
    fecha_hora: datetime,
    armo: bool,
    cierre_de: int | None,
) -> str:
    documento = {
        "anterior": anterior,
        "tipo": tipo,
        "proyecto_id": proyecto_id,
        "version": version,
        "huella_version": huella_version,
        "resultado": resultado,
        "notas": notas,
        "usuario": usuario,
        "fecha_hora": fecha_hora.isoformat(),
        "armo": armo,
        "cierre_de": cierre_de,
    }
    texto = json.dumps(documento, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _huella_del_evento(evento: EventoAprobacion) -> str:
    return _huella(
        anterior=evento.anterior,
        tipo=evento.tipo,
        proyecto_id=evento.proyecto_id,
        version=evento.version,
        huella_version=evento.huella_version,
        resultado=evento.resultado,
        notas=evento.notas,
        usuario=evento.usuario,
        fecha_hora=evento.fecha_hora,
        armo=evento.armo,
        cierre_de=evento.cierre_de,
    )


def _insertar(sesion: Session, *, anterior: str, **campos) -> FilaEventoAprobacion:
    fila = FilaEventoAprobacion(
        **campos, anterior=anterior, huella=_huella(anterior=anterior, **campos)
    )
    sesion.add(fila)
    sesion.flush()
    return fila


def _obra(sesion: Session, referencia: str) -> models.Proyecto:
    obra = resolver_proyecto(sesion, referencia)
    if obra is None:
        raise AprobacionInvalida(f"No se encontró la obra «{referencia}».")
    return obra


def _version(sesion: Session, obra: models.Proyecto, codigo: str) -> models.Presupuesto:
    presupuesto = sesion.scalars(
        select(models.Presupuesto).where(
            models.Presupuesto.proyecto_id == obra.id, models.Presupuesto.codigo == codigo
        )
    ).first()
    if presupuesto is None:
        raise AprobacionInvalida(f"No se encontró la versión {codigo} de esta obra.")
    return presupuesto


def _eslabon(sesion: Session, presupuesto: models.Presupuesto) -> EslabonVersion:
    eslabon = sesion.get(EslabonVersion, presupuesto.id)
    if eslabon is None:
        raise AprobacionInvalida(f"La versión {presupuesto.codigo} no está sellada.")
    return eslabon


def _sello(sesion: Session, presupuesto: models.Presupuesto) -> str:
    return _eslabon(sesion, presupuesto).huella_eslabon


def _quien_guardo(sesion: Session, presupuesto: models.Presupuesto) -> str:
    return _eslabon(sesion, presupuesto).usuario


def _armo(usuario: str, quien_guardo: str) -> bool:
    """Quien actúa es quien guardó la versión: por su cuenta (`<login>`) si las dos la traen
    (así un cambio de nombre no la oculta); si no, por el texto completo."""
    propio, de_la_version = login_de(usuario), login_de(quien_guardo)
    if propio is not None and de_la_version is not None:
        return propio == de_la_version
    return usuario.strip() == quien_guardo.strip()


def _notas_validas(notas: str) -> str:
    limpias = notas.strip()
    if len(limpias) > _LARGO_DE_NOTAS:
        raise AprobacionInvalida(NOTAS_LARGAS)
    return limpias


def _eventos(sesion: Session, proyecto_id: int) -> list[EventoAprobacion]:
    filas = sesion.scalars(
        select(FilaEventoAprobacion)
        .where(FilaEventoAprobacion.proyecto_id == proyecto_id)
        .order_by(FilaEventoAprobacion.id)
        .execution_options(populate_existing=True)
    )
    return [
        EventoAprobacion(
            id=f.id,
            proyecto_id=f.proyecto_id,
            tipo=f.tipo,
            version=f.version,
            huella_version=f.huella_version,
            resultado=f.resultado,
            notas=f.notas,
            usuario=f.usuario,
            fecha_hora=f.fecha_hora,
            armo=f.armo,
            cierre_de=f.cierre_de,
            anterior=f.anterior,
            huella=f.huella,
        )
        for f in filas
    ]


def _estado_del_evento(evento: EventoAprobacion) -> str:
    if evento.tipo == "envio":
        return "en_aprobacion"
    if evento.tipo == "retiro":
        return "retirada"
    return evento.resultado or ""


def _estados_por_version(eventos: Sequence[EventoAprobacion]) -> dict[str, EstadoDeVersion]:
    """El último movimiento de cada versión manda."""
    return {
        e.version: EstadoDeVersion(_estado_del_evento(e), e.usuario, e.fecha_hora, e.notas, e.armo)
        for e in eventos
    }


def _pendiente(eventos: Sequence[EventoAprobacion]) -> EventoAprobacion | None:
    """El envío de la obra que aún no tiene retiro ni dictamen (a lo sumo uno)."""
    cerrados = {e.cierre_de for e in eventos if e.cierre_de is not None}
    abiertos = [e for e in eventos if e.tipo == "envio" and e.id not in cerrados]
    return abiertos[-1] if abiertos else None


def _exigir_que_se_pueda_enviar(version: str, estado: str) -> None:
    if estado == "en_aprobacion":
        raise AprobacionInvalida(f"La versión {version} ya está en aprobación.")
    if estado in APROBADAS:
        raise AprobacionInvalida(f"La versión {version} ya está aprobada.")
    if estado == "devuelta":
        raise AprobacionInvalida(
            f"La versión {version} fue devuelta: corríjala en una versión nueva y envíe esa."
        )
