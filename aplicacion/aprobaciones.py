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

    huella = sha256(json_canonico({anterior, tipo, proyecto_id, version, huella_version,
                                   resultado, notas, usuario, fecha_hora (isoformat), armo,
                                   cierre_de}))

`json_canonico` y `huella` son los de `core/budget/canonico.py` (claves ordenadas, sin espacios,
UTF-8 sin escapar: los mismos bytes que la fórmula del plan). `ahora` va **sin zona horaria** (la
hora local de la instalación, como `api.sesion_web.ahora`): SQLite guarda la hora sin zona, así que
una huella calculada con «+00:00» no se podría recalcular; un `ahora` con zona es un `ValueError`
antes de escribir. `verificar_rastro` recalcula cada huella y su encadenamiento y compara el sello
guardado con el eslabón actual de la versión. Borrar el último evento no se detecta (límite de
toda cadena sin ancla externa, igual que la del núcleo).

**Todo o nada.** `enviar` y `dictaminar` confirman (`commit`) sus filas juntas o ninguna. La
concurrencia la guarda la base: `cierre_de` único (un envío se cierra una vez) y (`proyecto_id`,
`anterior`) único (dos eventos no cuelgan del mismo eslabón). Si la escritura choca con otra sesión
(`IntegrityError` por esas restricciones, o un `OperationalError` cuyo código de SQLite empieza por
`SQLITE_BUSY` o `SQLITE_LOCKED`, como el `SQLITE_BUSY_SNAPSHOT` de una lectura que quedó vieja en
WAL), se deshace, se relee y se valida una vez más; si vuelve a chocar, `CHOQUE`. Cualquier otro
error de la base sale tal cual. Con una sesión de `BEGIN IMMEDIATE` (la de las rutas de la API) el
segundo dictamen espera al primero y recibe siempre «Este envío ya tiene dictamen o fue
retirado.»; con una sesión común, el reintento lo da casi siempre, y si no, `CHOQUE`. En ningún
caso queda rastro doble.

**Lecturas para la API y la mesa (Tarea 18).** `envios` y `envio` dan cada envío con su desenlace
(para el índice de la instalación y el detalle de un envío); `armo_la_version` dice si una cuenta
guardó la versión de un envío; `pendientes_de_aprobacion` es la fuente «aprobar» de la mesa
(`aplicacion.mesa.FUENTES`). Las clases `NoSeEncontro` (404) y `DatosInvalidos` (422) afinan
`AprobacionInvalida` (409) para la API.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from aplicacion.proyectos import resolver_proyecto
from aplicacion.revision import login_de
from aplicacion.tablas_aprobacion import FilaEventoAprobacion
from core import models
from core.budget.cadena import GENESIS
from core.budget.canonico import huella as sha256_hex
from core.budget.canonico import json_canonico
from core.models.cadena import EslabonVersion

if TYPE_CHECKING:
    from aplicacion.mesa import Pendiente

__all__ = [
    "APROBADAS",
    "ESTADOS",
    "RESULTADOS",
    "AprobacionInvalida",
    "DatosInvalidos",
    "Envio",
    "EnvioRegistrado",
    "EstadoDeVersion",
    "EventoAprobacion",
    "NoSeEncontro",
    "RastroVerificado",
    "armo_la_version",
    "dictaminar",
    "enviar",
    "envio",
    "envios",
    "estados",
    "fases",
    "historial",
    "pendientes_de_aprobacion",
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
CON_ZONA_HORARIA = (
    "La hora del movimiento va sin zona horaria (la hora local de la instalación): SQLite la "
    "guarda sin zona y la huella no se podría recalcular."
)
#: Los códigos de SQLite (`sqlite3.Error.sqlite_errorname`) que son un choque entre sesiones.
_CODIGOS_DE_CHOQUE = ("SQLITE_BUSY", "SQLITE_LOCKED")
#: Cuántas letras de las notas de una devuelta caben en su pendiente de la mesa.
_LETRAS_EN_LA_MESA = 80
VER_EL_ENVIO = ("Ver el envío", "aprobar")
HACER_UNA_VERSION_NUEVA = ("Hacer una versión nueva", "hoja")


class AprobacionInvalida(ValueError):  # noqa: N818
    """Lo que la regla no permite por el estado de la obra o del envío (la API: 409), con un
    mensaje en lenguaje llano. Sus subclases afinan la respuesta."""


class NoSeEncontro(AprobacionInvalida):
    """La obra, la versión o el envío no existen en esta carpeta (la API: 404)."""


class DatosInvalidos(AprobacionInvalida):
    """Lo escrito no sirve: notas obligatorias que faltan, notas demasiado largas, un dictamen que
    no existe (la API: 422)."""


@dataclass(frozen=True, slots=True)
class Envio:
    id: int
    retirada: str | None  # la versión que estaba pendiente y este envío retiró


@dataclass(frozen=True, slots=True)
class EnvioRegistrado:
    """Un envío de la carpeta con su desenlace: `estado` es `en_aprobacion` mientras nadie lo
    cierra, o `retirada` o el resultado de su dictamen; `cerrado_por`/`cerrado_el` son de quien lo
    cerró (retiro o dictamen); `notas` son las del dictamen (vacías sin él) y `armo` dice si quien
    lo cerró es quien guardó la versión (como `EstadoDeVersion.armo`; falso si sigue abierto)."""

    id: int
    proyecto_id: int
    version: str
    nota: str
    por: str
    el: datetime
    estado: str
    cerrado_por: str | None
    cerrado_el: datetime | None
    notas: str
    armo: bool


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
    transacción y `Envio.retirada` lo nombra. Confirma; `AprobacionInvalida` si no se puede;
    `ValueError` si `ahora` trae zona horaria."""
    _exigir_hora_sin_zona(ahora)

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
    si el envío no existe, ya está cerrado o el dictamen no es válido; `ValueError` si `ahora`
    trae zona horaria."""
    _exigir_hora_sin_zona(ahora)

    def operacion() -> int:
        envio = sesion.get(FilaEventoAprobacion, envio_id, populate_existing=True)
        if envio is None or envio.tipo != "envio":
            raise NoSeEncontro(SIN_ENVIO)
        cerrado = sesion.scalar(
            select(FilaEventoAprobacion.id).where(FilaEventoAprobacion.cierre_de == envio_id)
        )
        if cerrado is not None:
            raise AprobacionInvalida(CERRADO)
        if resultado not in RESULTADOS:
            raise DatosInvalidos(DICTAMEN_DESCONOCIDO)
        notas_limpias = _notas_validas(notas)
        if resultado in _CON_NOTAS_OBLIGATORIAS and not notas_limpias:
            raise DatosInvalidos(SIN_NOTAS)
        obra = sesion.get(models.Proyecto, envio.proyecto_id)
        if obra is None:  # la obra se borró después del envío: no hay a qué atar el dictamen
            raise NoSeEncontro(SIN_ENVIO)
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


def envios(sesion: Session) -> list[EnvioRegistrado]:
    """Todos los envíos de la carpeta (de todas sus obras), en el orden del rastro, cada uno con
    su desenlace. Es lo que el índice de la instalación refleja."""
    filas = sesion.scalars(
        select(FilaEventoAprobacion)
        .order_by(FilaEventoAprobacion.id)
        .execution_options(populate_existing=True)
    ).all()
    cierres = {f.cierre_de: f for f in filas if f.cierre_de is not None}
    return [_registrado(f, cierres.get(f.id)) for f in filas if f.tipo == "envio"]


def envio(sesion: Session, envio_id: int) -> EnvioRegistrado:
    """El envío `envio_id` de esta carpeta con su desenlace; `NoSeEncontro` si no hay un envío
    con ese número (un retiro o un dictamen no son envíos)."""
    fila = sesion.get(FilaEventoAprobacion, envio_id, populate_existing=True)
    if fila is None or fila.tipo != "envio":
        raise NoSeEncontro(SIN_ENVIO)
    cierre = sesion.scalars(
        select(FilaEventoAprobacion).where(FilaEventoAprobacion.cierre_de == envio_id)
    ).one_or_none()
    return _registrado(fila, cierre)


def armo_la_version(sesion: Session, envio_id: int, usuario: str) -> bool:
    """Si `usuario` es quien guardó la versión del envío `envio_id` (por su cuenta, como `armo`
    de los eventos): lo que el panel del dictamen avisa antes de dictaminar."""
    registrado = envio(sesion, envio_id)
    obra = sesion.get(models.Proyecto, registrado.proyecto_id)
    if obra is None:
        raise NoSeEncontro(SIN_ENVIO)
    return _armo(usuario, _quien_guardo(sesion, _version(sesion, obra, registrado.version)))


def pendientes_de_aprobacion(sesion: Session, hoy: date) -> list[Pendiente]:
    """La fuente «aprobar» de la mesa (`aplicacion.mesa.FuentePendientes`), sobre el ÚLTIMO envío
    de cada obra, en orden alfabético de obra: en aprobación → «{versión} espera dictamen»
    («Ver el envío»); devuelta → «{versión} devuelta: {primeras 80 letras de las notas}»
    («Hacer una versión nueva»; los espacios y saltos de línea seguidos cuentan como uno y, si se
    cortan, termina en «…»). Una devuelta deja de ser pendiente cuando la obra envía otra versión;
    aprobada o retirada no son pendientes."""
    # `aplicacion.mesa` se importa aquí y no arriba: la mesa lee los estados de este módulo para
    # sus etapas, y las dos importaciones arriba formarían un ciclo.
    from aplicacion.mesa import Pendiente, Siguiente

    del hoy  # la regla no depende del día
    ultimos: dict[int, EnvioRegistrado] = {}
    for registrado in envios(sesion):
        ultimos[registrado.proyecto_id] = registrado
    if not ultimos:
        return []
    obras = sesion.scalars(
        select(models.Proyecto)
        .where(models.Proyecto.id.in_(ultimos))
        .order_by(models.Proyecto.nombre, models.Proyecto.id)
    )
    salida = []
    for obra in obras:
        ultimo = ultimos[obra.id]
        if ultimo.estado == "en_aprobacion":
            texto, accion = f"{ultimo.version} espera dictamen", VER_EL_ENVIO
        elif ultimo.estado == "devuelta":
            texto = f"{ultimo.version} devuelta: {_primeras_letras(ultimo.notas)}"
            accion = HACER_UNA_VERSION_NUEVA
        else:
            continue
        salida.append(Pendiente(str(obra.id), obra.nombre, texto, Siguiente(*accion)))
    return salida


# --- ayudantes ----------------------------------------------------------------------------------


def _registrado(fila: FilaEventoAprobacion, cierre: FilaEventoAprobacion | None) -> EnvioRegistrado:
    dictamen = cierre is not None and cierre.tipo == "dictamen"
    return EnvioRegistrado(
        id=fila.id,
        proyecto_id=fila.proyecto_id,
        version=fila.version,
        nota=fila.notas,
        por=fila.usuario,
        el=fila.fecha_hora,
        estado="en_aprobacion" if cierre is None else _estado_del_evento(cierre),
        cerrado_por=None if cierre is None else cierre.usuario,
        cerrado_el=None if cierre is None else cierre.fecha_hora,
        notas=cierre.notas if dictamen else "",
        armo=cierre is not None and cierre.armo,
    )


def _primeras_letras(notas: str) -> str:
    seguidas = " ".join(notas.split())
    if len(seguidas) <= _LETRAS_EN_LA_MESA:
        return seguidas
    return seguidas[:_LETRAS_EN_LA_MESA] + "…"


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
        if isinstance(error, OperationalError) and not _es_choque(error):
            raise
        raise _ChoqueDeEscritura from error
    except BaseException:
        sesion.rollback()
        raise
    return resultado


def _es_choque(error: OperationalError) -> bool:
    """Un choque entre sesiones según el código de SQLite (`SQLITE_BUSY*`, `SQLITE_LOCKED*`), no
    según el texto del error. Un error sin código no es un choque."""
    nombre = getattr(error.orig, "sqlite_errorname", "") or ""
    return nombre.startswith(_CODIGOS_DE_CHOQUE)


def _exigir_hora_sin_zona(ahora: datetime) -> None:
    if ahora.tzinfo is not None:
        raise ValueError(CON_ZONA_HORARIA)


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
    return sha256_hex(json_canonico(documento))


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
        raise NoSeEncontro(f"No se encontró la obra «{referencia}».")
    return obra


def _version(sesion: Session, obra: models.Proyecto, codigo: str) -> models.Presupuesto:
    presupuesto = sesion.scalars(
        select(models.Presupuesto).where(
            models.Presupuesto.proyecto_id == obra.id, models.Presupuesto.codigo == codigo
        )
    ).first()
    if presupuesto is None:
        raise NoSeEncontro(f"No se encontró la versión {codigo} de esta obra.")
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
        raise DatosInvalidos(NOTAS_LARGAS)
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


def _estado_del_evento(evento: EventoAprobacion | FilaEventoAprobacion) -> str:
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
