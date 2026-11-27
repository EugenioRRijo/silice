"""Notificaciones por evento y qué recibir (C11b y Lote G5; especificación
`docs/especificaciones/2026-11-26-notificaciones-por-evento.md`, acordada con Eugenio el
2026-11-26).

El servidor crea notificaciones cuando pasa algo y se las deja a quienes les importa. Cinco
categorías (`Categoria`), todas encendidas por omisión; cada persona puede apagarlas, salvo la 1
para quien revisa:

1. `por_dictaminar`: una versión espera su dictamen (para quienes revisan, menos quien la envió) y,
   desde los 2 días hábiles de espera, un recordatorio (Advertencia).
2. `dictamen`: su versión fue aprobada, aprobada con observaciones, devuelta (Advertencia) o
   retirada (otra cuenta envió una versión nueva de la obra), para quien la envió. Nada si la cerró
   esa misma cuenta.
3. `compras`: un material de una obra en la que la persona trabajó (guardó o envió una versión) y
   que aún no se pidió: Advertencia desde 2 días hábiles antes de «pedir a más tardar» y Error desde
   ese día, las mismas alertas de `aplicacion.procura.alertas_de_compra` (con los feriados de la
   línea base). Sin línea base no hay fechas y no hay aviso.
4. `listas_de_precios`: se cargó una lista de la empresa o la referencia MaPreX, para quienes arman
   (menos quien la cargó).
5. `entregas`: una obra en la que la persona trabajó tiene fecha de entrega al cliente y aún no se
   ha entregado: Advertencia desde 3 días hábiles antes y Error desde el día de la entrega.

**Una sola vez por evento.** Cada notificación lleva una clave (`aprobacion:<carpeta>:<envío>:
<versión>:enviada`, `compra:…`, `lista:…`, `entrega:…`) y la base no admite dos iguales para una
persona (`notificaciones.agregar`, índice único). Como la retención es de 30 días, una clave vuelve
a quedar libre a los 30 días: un recordatorio, una compra vencida o una entrega vencida que siguen
igual se repiten una vez al mes.

**Dónde nace cada una.** Las de un momento (envío, dictamen, retiro, lista nueva) las crean los
ganchos `de_aprobaciones` (lo llama `indice_aprobaciones.escribir_reflejo` al cambiar el índice) y
`lista_cargada` (las rutas de Precios de la empresa, tras confirmar la carpeta). Las que dependen de
la fecha (recordatorio, compras y entregas) las calcula `barrer` al listar
(`GET /v1/notificaciones`), sin hilo de fondo y solo para quien lista; las compras y entregas, en la
carpeta que esa persona tiene abierta.

**Nunca rompen lo que avisan.** Un fallo al avisar se registra y se descarta (cada inserción va en
su propio `SAVEPOINT`): el índice, la lista o el listado siguen igual. Las funciones solo hacen
`flush`, nunca `commit`: la transacción de `instalacion.db` es de quien llama.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable, Collection, Iterable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion import aprobaciones, entrega_de_obra, indice_aprobaciones, notificaciones, procura
from aplicacion.indice_aprobaciones import FilaIndice
from aplicacion.mesa import dias_habiles_entre
from aplicacion.notificaciones import (
    MAX_CLAVE_EVENTO,
    MAX_DETALLE,
    MAX_TITULO,
    RETENCION,
    DatosNotificacion,
)
from aplicacion.plural import plural
from aplicacion.revision import login_de
from core import models
from core.budget.calendario import es_habil
from core.budget.valuaciones import linea_base_vigente
from core.models.cadena import EslabonVersion
from seguridad.modelo import EventoAcceso, PreferenciaNotificacion, Usuario
from seguridad.permisos import Rol, roles_de
from seguridad.sesiones import SesionActiva

__all__ = [
    "CATEGORIAS",
    "DIAS_AVISO_ENTREGA",
    "DIAS_PARA_RECORDAR",
    "MENSAJE_OBLIGATORIA",
    "RUTA_DE_LAS_LISTAS",
    "Categoria",
    "DefinicionCategoria",
    "Evento",
    "Preferencia",
    "PreferenciaInvalida",
    "barrer",
    "de_aprobaciones",
    "emitir",
    "fijar_preferencias",
    "lista_cargada",
    "preferencias",
]

_registro = logging.getLogger(__name__)

#: Días hábiles de espera de un envío desde los que se recuerda a quien revisa.
DIAS_PARA_RECORDAR = 2
#: Días hábiles antes de la fecha de entrega al cliente desde los que se avisa.
DIAS_AVISO_ENTREGA = 3
#: Precios de la empresa en la interfaz (`frontend-desktop/src/marco/espacios.ts`).
RUTA_DE_LAS_LISTAS = "/precios/listas"
#: El segmento de la carpeta de la empresa en las rutas de obra (`marco/secciones.ts`).
_SEGMENTO_DE_LA_EMPRESA = "empresa"
_VER_LA_APROBACION = "Ver la aprobación"
_VER_LAS_LISTAS = "Ver los precios de la empresa"
_VER_EL_RESUMEN = "Ver el resumen de la obra"
_SECCION_RESUMEN = "resumen"
_TEXTO_PROCURA, _SECCION_PROCURA = procura.VER_LA_PROCURA

MENSAJE_OBLIGATORIA = (
    "Quien revisa recibe siempre las versiones que esperan su dictamen: esa categoría no se "
    "puede apagar."
)


class Categoria(StrEnum):
    POR_DICTAMINAR = "por_dictaminar"
    DICTAMEN = "dictamen"
    COMPRAS = "compras"
    LISTAS_DE_PRECIOS = "listas_de_precios"
    ENTREGAS = "entregas"


@dataclass(frozen=True, slots=True)
class DefinicionCategoria:
    """Una categoría: su nombre en Cuenta › Notificaciones, la frase de qué avisa, los roles a los
    que les llega y los roles para los que no se puede apagar."""

    categoria: Categoria
    titulo: str
    descripcion: str
    roles: frozenset[Rol]
    obligatoria_para: frozenset[Rol] = frozenset()


CATEGORIAS: tuple[DefinicionCategoria, ...] = (
    DefinicionCategoria(
        Categoria.POR_DICTAMINAR,
        "Versiones por dictaminar",
        "Una versión espera su dictamen, y un recordatorio si lleva 2 días hábiles esperando.",
        frozenset({Rol.REVISA}),
        frozenset({Rol.REVISA}),
    ),
    DefinicionCategoria(
        Categoria.DICTAMEN,
        "Dictamen de sus versiones",
        "Una versión que usted envió fue aprobada, devuelta o retirada.",
        frozenset({Rol.ARMA}),
    ),
    DefinicionCategoria(
        Categoria.COMPRAS,
        "Compras por pedir",
        "Un material de una obra en la que trabajó debe pedirse pronto o ya debía pedirse.",
        frozenset({Rol.ARMA}),
    ),
    DefinicionCategoria(
        Categoria.LISTAS_DE_PRECIOS,
        "Listas de precios nuevas",
        "Se cargó una lista o una referencia de precios nueva.",
        frozenset({Rol.ARMA}),
    ),
    DefinicionCategoria(
        Categoria.ENTREGAS,
        "Entregas al cliente",
        "Se acerca o ya llegó la fecha de entrega al cliente de una obra en la que trabajó.",
        frozenset({Rol.ARMA}),
    ),
)
_POR_CATEGORIA = {d.categoria.value: d for d in CATEGORIAS}


class PreferenciaInvalida(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """Lo pedido en las preferencias no se puede guardar; el mensaje es el que ve la persona."""


@dataclass(frozen=True, slots=True)
class Preferencia:
    """Lo que ve la persona por categoría: si la recibe (`activa`), si le llega por su rol
    (`aplica`) y si no la puede apagar (`obligatoria`)."""

    categoria: str
    titulo: str
    descripcion: str
    activa: bool
    aplica: bool
    obligatoria: bool


@dataclass(frozen=True, slots=True)
class Evento:
    """Una notificación por crear: su clave (una vez por persona) y lo que ve la persona."""

    clave: str
    gravedad: str
    titulo: str
    detalle: str = ""
    enlace_texto: str = ""
    enlace_ruta: str = ""


# --- preferencias ---------------------------------------------------------------------------------


def _roles(sesion: Session, usuario_id: int) -> frozenset[Rol]:
    usuario = sesion.get(Usuario, usuario_id)
    return frozenset() if usuario is None else roles_de(usuario.roles)


def _guardadas(sesion: Session, usuario_id: int) -> dict[str, bool]:
    filas = sesion.scalars(
        select(PreferenciaNotificacion).where(PreferenciaNotificacion.usuario_id == usuario_id)
    )
    return {f.categoria: bool(f.activa) for f in filas}


def _obligatoria(definicion: DefinicionCategoria, roles: frozenset[Rol]) -> bool:
    return bool(definicion.obligatoria_para & roles)


def preferencias(sesion: Session, usuario_id: int) -> list[Preferencia]:
    """Las cuatro categorías de `usuario_id`, en su orden, con lo elegido (sin fila, encendida)."""
    roles, guardadas = _roles(sesion, usuario_id), _guardadas(sesion, usuario_id)
    salida = []
    for definicion in CATEGORIAS:
        obligatoria = _obligatoria(definicion, roles)
        salida.append(
            Preferencia(
                categoria=definicion.categoria.value,
                titulo=definicion.titulo,
                descripcion=definicion.descripcion,
                activa=obligatoria or guardadas.get(definicion.categoria.value, True),
                aplica=bool(definicion.roles & roles),
                obligatoria=obligatoria,
            )
        )
    return salida


def fijar_preferencias(
    sesion: Session, usuario_id: int, cambios: Sequence[tuple[str, bool]]
) -> list[Preferencia]:
    """Enciende o apaga las categorías de `cambios` para `usuario_id` (solo `flush`) y devuelve
    todas. `PreferenciaInvalida` (sin escribir nada) ante una categoría desconocida o repetida, o
    al apagar una que es obligatoria para su rol."""
    roles = _roles(sesion, usuario_id)
    vistas: set[str] = set()
    for categoria, activa in cambios:
        definicion = _POR_CATEGORIA.get(categoria)
        if definicion is None:
            raise PreferenciaInvalida(f"No existe la categoría «{categoria}».")
        if categoria in vistas:
            raise PreferenciaInvalida(f"La categoría «{categoria}» está repetida.")
        vistas.add(categoria)
        if not activa and _obligatoria(definicion, roles):
            raise PreferenciaInvalida(MENSAJE_OBLIGATORIA)
    for categoria, activa in cambios:
        fila = sesion.get(PreferenciaNotificacion, (usuario_id, categoria))
        if fila is None:
            sesion.add(
                PreferenciaNotificacion(usuario_id=usuario_id, categoria=categoria, activa=activa)
            )
        else:
            fila.activa = activa
    sesion.flush()
    return preferencias(sesion, usuario_id)


def _activa(sesion: Session, usuario_id: int, categoria: Categoria) -> bool:
    definicion = _POR_CATEGORIA[categoria.value]
    if _obligatoria(definicion, _roles(sesion, usuario_id)):
        return True
    fila = sesion.get(PreferenciaNotificacion, (usuario_id, categoria.value))
    return True if fila is None else bool(fila.activa)


# --- emitir ---------------------------------------------------------------------------------------


def emitir(
    sesion: Session,
    categoria: Categoria,
    evento: Evento,
    destinatarios: Iterable[int],
    ahora: datetime,
) -> list[int]:
    """Crea la notificación de `evento` para cada destinatario que tenga `categoria` encendida y
    aún no la tenga (por su clave). Devuelve a quiénes se la creó, en orden de `id`. Solo `flush`;
    una clave que otra petición acaba de escribir (choque del índice único) se absorbe. Un enlace
    que no es una ruta interna válida (una carpeta de nombre larguísimo) se quita: el aviso
    llega igual."""
    texto, ruta = evento.enlace_texto, evento.enlace_ruta
    try:
        notificaciones.validar_ruta(ruta)
    except ValueError:
        texto, ruta = "", ""
    datos = DatosNotificacion(
        gravedad=evento.gravedad,
        titulo=_recortar(evento.titulo, MAX_TITULO),
        detalle=_recortar(evento.detalle, MAX_DETALLE),
        enlace_texto=texto,
        enlace_ruta=ruta,
    )
    creados = []
    for usuario_id in sorted(set(destinatarios)):
        if not _activa(sesion, usuario_id, categoria):
            continue
        if notificaciones.existe_clave(sesion, usuario_id, evento.clave):
            continue
        try:
            with sesion.begin_nested():
                notificaciones.agregar(sesion, usuario_id, datos, ahora, clave_evento=evento.clave)
        except IntegrityError:
            continue
        creados.append(usuario_id)
    return creados


def _cuentas_con(sesion: Session, rol: Rol, *, excepto: Iterable[int] = ()) -> list[int]:
    """Las cuentas activas con `rol`, menos las de `excepto`."""
    fuera = set(excepto)
    return [
        u.id
        for u in sesion.scalars(select(Usuario).where(Usuario.activo.is_(True)))
        if rol in roles_de(u.roles) and u.id not in fuera
    ]


def _cuenta_de(sesion: Session, responsable: str) -> int | None:
    """La cuenta activa de un responsable `Nombre <login>`; `None` sin `<login>` o sin cuenta."""
    login = login_de(responsable)
    if login is None:
        return None
    return sesion.scalar(select(Usuario.id).where(Usuario.login == login, Usuario.activo.is_(True)))


# --- textos, claves y rutas -----------------------------------------------------------------------


def _recortar(texto: str, largo: int) -> str:
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


def _nombre(responsable: str) -> str:
    """`Ana` de `Ana <ana>` (y de `Ana <ana> (tras restablecimiento)`)."""
    return re.sub(r"\s*<[^>]*>.*$", "", responsable).strip() or responsable.strip()


def _dia(momento: date | datetime) -> str:
    return f"{momento:%d/%m/%Y}"


def _clave(*partes: object) -> str:
    """Las partes unidas con «:»; si no caben en la columna, un prefijo y su huella."""
    clave = ":".join(str(p) for p in partes)
    if len(clave) <= MAX_CLAVE_EVENTO:
        return clave
    huella = hashlib.sha256(clave.encode("utf-8")).hexdigest()
    return f"{clave[: MAX_CLAVE_EVENTO - len(huella) - 1]}:{huella}"


def _segmento(caso: str | None, carpeta_empresa: str | None) -> str:
    """La carpeta en una ruta de obra: `empresa` para la de la empresa (o sin archivo)."""
    if caso is None or caso == carpeta_empresa:
        return _SEGMENTO_DE_LA_EMPRESA
    return quote(caso, safe="")


def _ruta_de_obra(caso: str | None, carpeta_empresa: str | None, obra: str, seccion: str) -> str:
    return f"/obra/{_segmento(caso, carpeta_empresa)}/{quote(obra, safe='')}/{seccion}"


# --- categorías 1 y 2: el índice de aprobaciones --------------------------------------------------

_DICTAMENES = {
    "aprobada": ("info", "fue aprobada", "la aprobó"),
    "aprobada_con_observaciones": (
        "info",
        "fue aprobada con observaciones",
        "la aprobó con observaciones",
    ),
    "devuelta": ("advertencia", "fue devuelta", "la devolvió"),
}


def de_aprobaciones(
    sesion: Session,
    antes: Sequence[FilaIndice],
    despues: Sequence[FilaIndice],
    ahora: datetime,
    *,
    carpeta_empresa: str | None,
) -> None:
    """El gancho del índice de aprobaciones: compara las filas de una carpeta antes y después de
    reflejarla y avisa lo que cambió. Un envío que pasa a esperar dictamen avisa a quienes revisan
    (menos a quien lo envió); uno que se cierra (dictamen o retiro) avisa a quien lo envió, si el
    cierre es de los últimos 30 días. Un fallo se registra y no sale de aquí."""
    try:
        previas = {(f.caso, f.envio_id): f for f in antes}
        for fila in despues:
            previa = previas.get((fila.caso, fila.envio_id))
            if fila.estado == "en_aprobacion":
                if previa is None or previa.estado != "en_aprobacion":
                    _avisar_envio(sesion, fila, ahora, carpeta_empresa)
            elif previa is None or previa.estado != fila.estado:
                _avisar_cierre(sesion, fila, despues, ahora, carpeta_empresa)
    except Exception:  # noqa: BLE001 (avisar nunca desdice el índice)
        _registro.warning("No se pudieron crear los avisos de aprobaciones.", exc_info=True)


def _ruta_aprobacion(fila: FilaIndice, carpeta_empresa: str | None) -> str:
    return _ruta_de_obra(fila.caso, carpeta_empresa, fila.proyecto, "aprobaciones")


def _clave_aprobacion(fila: FilaIndice, que: str) -> str:
    return _clave("aprobacion", fila.caso, fila.envio_id, fila.version, que)


def _avisar_envio(
    sesion: Session, fila: FilaIndice, ahora: datetime, carpeta_empresa: str | None
) -> None:
    remitente = _cuenta_de(sesion, fila.enviado_por)
    detalle = f"La envió {_nombre(fila.enviado_por)} el {_dia(fila.enviado_el)}."
    if fila.nota.strip():
        detalle += f" Nota: {fila.nota.strip()}"
    evento = Evento(
        clave=_clave_aprobacion(fila, "enviada"),
        gravedad="info",
        titulo=f"{fila.version} de «{fila.obra}» espera su dictamen",
        detalle=detalle,
        enlace_texto=_VER_LA_APROBACION,
        enlace_ruta=_ruta_aprobacion(fila, carpeta_empresa),
    )
    excepto = () if remitente is None else (remitente,)
    emitir(
        sesion,
        Categoria.POR_DICTAMINAR,
        evento,
        _cuentas_con(sesion, Rol.REVISA, excepto=excepto),
        ahora,
    )


def _quien_retiro(fila: FilaIndice, filas: Sequence[FilaIndice]) -> FilaIndice | None:
    """El envío que retiró a `fila`: el siguiente envío de la misma obra en la misma carpeta."""
    siguientes = [
        f
        for f in filas
        if f.caso == fila.caso and f.proyecto == fila.proyecto and f.envio_id > fila.envio_id
    ]
    return min(siguientes, key=lambda f: f.envio_id, default=None)


def _avisar_cierre(
    sesion: Session,
    fila: FilaIndice,
    filas: Sequence[FilaIndice],
    ahora: datetime,
    carpeta_empresa: str | None,
) -> None:
    if fila.estado == "retirada":
        nuevo = _quien_retiro(fila, filas)
        if nuevo is None:
            return
        actor, cuando = nuevo.enviado_por, nuevo.enviado_el
        gravedad, desenlace = "info", "fue retirada"
        detalle = f"{_nombre(actor)} envió {nuevo.version} el {_dia(cuando)} y retiró la suya."
    elif fila.estado in _DICTAMENES and fila.dictamen_por and fila.dictamen_el:
        actor, cuando = fila.dictamen_por, fila.dictamen_el
        gravedad, desenlace, verbo = _DICTAMENES[fila.estado]
        detalle = f"{_nombre(actor)} {verbo} el {_dia(cuando)}."
        if fila.notas.strip():
            detalle += f" Notas: {fila.notas.strip()}"
    else:
        return
    if cuando < ahora - RETENCION or aprobaciones.misma_cuenta(actor, fila.enviado_por):
        return
    remitente = _cuenta_de(sesion, fila.enviado_por)
    if remitente is None:
        return
    evento = Evento(
        clave=_clave_aprobacion(fila, fila.estado),
        gravedad=gravedad,
        titulo=f"Su versión {fila.version} de «{fila.obra}» {desenlace}",
        detalle=detalle,
        enlace_texto=_VER_LA_APROBACION,
        enlace_ruta=_ruta_aprobacion(fila, carpeta_empresa),
    )
    emitir(sesion, Categoria.DICTAMEN, evento, [remitente], ahora)


# --- categoría 4: listas de precios ---------------------------------------------------------------


def lista_cargada(
    sesion: Session,
    *,
    caso: str | None,
    carpeta_empresa: str | None,
    lista_id: int,
    nombre: str,
    quien: SesionActiva,
    ahora: datetime,
) -> None:
    """El gancho de Precios de la empresa: se cargó la lista `nombre` (`lista_id`) en la carpeta
    `caso`. Avisa a quienes arman, menos a quien la cargó. Un fallo se registra y no sale."""
    try:
        if caso is None or caso == carpeta_empresa:
            donde = "en la carpeta de la empresa"
        else:
            donde = f"en la carpeta «{caso}»"
        evento = Evento(
            clave=_clave("lista", caso or _SEGMENTO_DE_LA_EMPRESA, lista_id),
            gravedad="info",
            titulo=f"Lista de precios nueva: «{nombre}»",
            detalle=f"{quien.nombre} la cargó {donde}.",
            enlace_texto=_VER_LAS_LISTAS,
            enlace_ruta=RUTA_DE_LAS_LISTAS,
        )
        destinatarios = _cuentas_con(sesion, Rol.ARMA, excepto=(quien.usuario_id,))
        emitir(sesion, Categoria.LISTAS_DE_PRECIOS, evento, destinatarios, ahora)
    except Exception:  # noqa: BLE001 (la lista ya está guardada: avisar no la desdice)
        _registro.warning("No se pudo avisar la lista de precios nueva.", exc_info=True)


# --- el barrido al listar: recordatorios, compras y entregas --------------------------------------


def barrer(
    sesion: Session,
    persona: SesionActiva,
    ahora: datetime,
    *,
    carpeta_empresa: str | None,
    caso: str | None,
    abrir_carpeta: Callable[[], AbstractContextManager[Session]] | None,
) -> None:
    """Lo que vence con la fecha, para `persona` y solo para ella (`GET /v1/notificaciones`):
    las compras por pedir y las entregas al cliente de las obras de la carpeta abierta (`caso`,
    que `abrir_carpeta` abre solo si alguna de las dos categorías está encendida) y el recordatorio
    de lo que espera su dictamen desde 2 días hábiles. Primero lee la carpeta y después escribe la
    instalación. Nada de esto falla hacia afuera: un error se registra y el listado sigue."""
    hoy = ahora.date()
    compras: list[Evento] = []
    entregas: list[Evento] = []
    if abrir_carpeta is not None and Rol.ARMA in persona.roles:
        ver_compras = _activa(sesion, persona.usuario_id, Categoria.COMPRAS)
        ver_entregas = _activa(sesion, persona.usuario_id, Categoria.ENTREGAS)
        if ver_compras or ver_entregas:
            entregados = _detalles_de_entregas(sesion) if ver_entregas else ()
            try:
                with abrir_carpeta() as sesion_caso:
                    if ver_compras:
                        compras = _compras(
                            sesion_caso, persona.usuario, hoy, caso, carpeta_empresa
                        )
                    if ver_entregas:
                        entregas = _entregas(
                            sesion_caso,
                            persona.usuario,
                            hoy,
                            caso,
                            carpeta_empresa,
                            entregados,
                        )
            except Exception:  # noqa: BLE001 (una carpeta que no abre no impide listar)
                _registro.warning("No se pudo revisar la carpeta %s.", caso, exc_info=True)
    try:
        for evento in compras:
            emitir(sesion, Categoria.COMPRAS, evento, [persona.usuario_id], ahora)
        for evento in entregas:
            emitir(sesion, Categoria.ENTREGAS, evento, [persona.usuario_id], ahora)
        if Rol.REVISA in persona.roles:
            _recordar(sesion, persona, ahora, carpeta_empresa)
    except Exception:  # noqa: BLE001 (el listado sigue aunque un aviso falle)
        _registro.warning("No se pudieron crear los avisos al listar.", exc_info=True)


def _recordar(
    sesion: Session, persona: SesionActiva, ahora: datetime, carpeta_empresa: str | None
) -> None:
    for fila in indice_aprobaciones.pendientes(sesion):
        if aprobaciones.misma_cuenta(persona.usuario, fila.enviado_por):
            continue
        # Lunes a viernes, sin feriados: una aprobación no tiene línea base con calendario de la
        # obra (ver `aplicacion.mesa.dias_habiles_entre` y la §2 de la especificación, #8).
        dias = dias_habiles_entre(fila.enviado_el.date(), ahora.date())
        if dias < DIAS_PARA_RECORDAR:
            continue
        evento = Evento(
            clave=_clave_aprobacion(fila, "recordatorio"),
            gravedad="advertencia",
            titulo=f"{fila.version} de «{fila.obra}» sigue esperando su dictamen",
            detalle=(
                f"Se envió el {_dia(fila.enviado_el)} y lleva "
                f"{plural(dias, 'día hábil', 'días hábiles')} sin dictamen."
            ),
            enlace_texto=_VER_LA_APROBACION,
            enlace_ruta=_ruta_aprobacion(fila, carpeta_empresa),
        )
        emitir(sesion, Categoria.POR_DICTAMINAR, evento, [persona.usuario_id], ahora)


def _obras_de(sesion_caso: Session, usuario: str) -> list[int]:
    """Las obras de la carpeta en las que `usuario` trabajó: guardó o envió una versión."""
    suyas = {
        proyecto_id
        for proyecto_id, quien in sesion_caso.execute(
            select(EslabonVersion.proyecto_id, EslabonVersion.usuario).distinct()
        )
        if aprobaciones.misma_cuenta(usuario, quien)
    }
    suyas |= {
        envio.proyecto_id
        for envio in aprobaciones.envios(sesion_caso)
        if aprobaciones.misma_cuenta(usuario, envio.por)
    }
    return sorted(suyas)


def _huella_material(necesidad: procura.NecesidadDeInsumo) -> str:
    texto = f"{necesidad.descripcion}\x1f{necesidad.unidad}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def _compras(
    sesion_caso: Session,
    usuario: str,
    hoy: date,
    caso: str | None,
    carpeta_empresa: str | None,
) -> list[Evento]:
    """Las compras por pedir al día `hoy` de las obras de `usuario` en esta carpeta: una por
    material sin pedir ni recibir, con la alerta de la procura (aviso o vencida)."""
    eventos = []
    for proyecto_id in _obras_de(sesion_caso, usuario):
        obra = sesion_caso.get(models.Proyecto, proyecto_id)
        if obra is None:
            continue
        leida = procura.procura(sesion_caso, obra.nombre)
        for necesidad in leida.necesidades:
            if necesidad.recibida is not None and necesidad.recibida <= hoy:
                continue  # llegó: una compra tardía no pide actuar
            alertas = procura.alertas_de_compra([necesidad], hoy, leida.feriados)
            if not alertas or necesidad.pedir_a_mas_tardar is None:
                continue
            vencida = alertas[0].severidad == procura.ERROR
            eventos.append(
                Evento(
                    clave=_clave(
                        "compra",
                        caso or _SEGMENTO_DE_LA_EMPRESA,
                        proyecto_id,
                        _huella_material(necesidad),
                        necesidad.pedir_a_mas_tardar.isoformat(),
                        "vencida" if vencida else "aviso",
                    ),
                    gravedad="error" if vencida else "advertencia",
                    titulo=alertas[0].texto,
                    detalle=(
                        f"Obra «{obra.nombre}». Anote el pedido en la procura cuando lo haga."
                    ),
                    enlace_texto=_TEXTO_PROCURA,
                    enlace_ruta=_ruta_de_obra(
                        caso, carpeta_empresa, str(proyecto_id), _SECCION_PROCURA
                    ),
                )
            )
    return eventos


def _detalles_de_entregas(sesion: Session) -> Sequence[tuple[datetime, str]]:
    """`(cuándo, detalle)` de los paquetes exportados registrados en `instalacion.db`."""
    return [
        (fecha_hora, detalle)
        for fecha_hora, detalle in sesion.execute(
            select(EventoAcceso.fecha_hora, EventoAcceso.detalle).where(
                EventoAcceso.tipo == "paquete exportado"
            )
        )
    ]


def _obra_entregada(
    sesion_caso: Session,
    proyecto_id: int,
    entregas_registradas: Sequence[tuple[datetime, str]],
    desde: datetime | None,
) -> bool:
    """True si alguna versión de la obra tiene un paquete exportado en la instalación desde `desde`
    (la última vez que se fijó la fecha de entrega, inclusive): uno exportado antes no es la
    entrega de esa fecha (auditoría antes de medicion-v1, #9). Las dos horas vienen del mismo
    reloj (`api.sesion_web.ahora`). Sin `desde`, cuenta cualquier exportación."""
    detalles = [
        detalle for cuando, detalle in entregas_registradas if desde is None or cuando >= desde
    ]
    if not detalles:
        return False
    sellos = sesion_caso.scalars(
        select(EslabonVersion.huella_eslabon)
        .join(models.Presupuesto, models.Presupuesto.id == EslabonVersion.presupuesto_id)
        .where(models.Presupuesto.proyecto_id == proyecto_id)
    ).all()
    return any(
        f"sello_version {sello}" in detalle
        for sello in sellos
        for detalle in detalles
    )


def _feriados_de_la_obra(sesion_caso: Session, nombre_obra: str) -> frozenset[date]:
    fila = linea_base_vigente(sesion_caso, nombre_obra, date.max)
    if fila is None or fila.calendario is None:
        return frozenset()
    return frozenset(date.fromisoformat(dia) for dia in json.loads(fila.calendario.feriados))


def _habiles_antes(fecha: date, dias: int, feriados: Collection[date]) -> date:
    """El día hábil que queda `dias` días hábiles antes de `fecha`."""
    dia = fecha
    while dias > 0:
        dia -= timedelta(days=1)
        if es_habil(dia, feriados):
            dias -= 1
    return dia


def _entregas(
    sesion_caso: Session,
    usuario: str,
    hoy: date,
    caso: str | None,
    carpeta_empresa: str | None,
    entregas_registradas: Sequence[tuple[datetime, str]],
) -> list[Evento]:
    """Las entregas al cliente al día `hoy` de las obras de `usuario` en esta carpeta que tienen
    fecha de entrega fijada y aún no se han entregado: Advertencia desde 3 días hábiles antes y
    Error desde el día de la entrega. El Error es uno por fecha (misma clave): el mismo día dice
    «Hoy vence la entrega…» y, si se lista por primera vez después, que «debía entregarse»
    (auditoría antes de medicion-v1, #7)."""
    fechas = entrega_de_obra.entregas_de_la_carpeta(sesion_caso)
    if not fechas:
        return []
    eventos = []
    for proyecto_id in _obras_de(sesion_caso, usuario):
        entrega = fechas.get(proyecto_id)
        if entrega is None or entrega.fecha_entrega is None:
            continue
        fecha_entrega = entrega.fecha_entrega
        obra = sesion_caso.get(models.Proyecto, proyecto_id)
        if obra is None or _obra_entregada(
            sesion_caso, proyecto_id, entregas_registradas, entrega.actualizada
        ):
            continue
        feriados = _feriados_de_la_obra(sesion_caso, obra.nombre)
        if hoy < _habiles_antes(fecha_entrega, DIAS_AVISO_ENTREGA, feriados):
            continue
        vencida = hoy >= fecha_entrega
        if hoy == fecha_entrega:
            titulo = f"Hoy vence la entrega de «{obra.nombre}»."
            detalle = (
                f"Obra «{obra.nombre}». La fecha de entrega al cliente es hoy, "
                f"{_dia(fecha_entrega)}."
            )
        elif vencida:
            titulo = (
                f"«{obra.nombre}» no está entregada y debía entregarse el "
                f"{_dia(fecha_entrega)}."
            )
            detalle = (
                f"Obra «{obra.nombre}». La fecha de entrega al cliente era el "
                f"{_dia(fecha_entrega)}."
            )
        else:
            titulo = f"Entregue «{obra.nombre}» antes del {_dia(fecha_entrega)}."
            detalle = (
                f"Obra «{obra.nombre}». La fecha de entrega al cliente es el "
                f"{_dia(fecha_entrega)}."
            )
        eventos.append(
            Evento(
                clave=_clave(
                    "entrega",
                    caso or _SEGMENTO_DE_LA_EMPRESA,
                    proyecto_id,
                    fecha_entrega.isoformat(),
                    "vencida" if vencida else "aviso",
                ),
                gravedad="error" if vencida else "advertencia",
                titulo=titulo,
                detalle=detalle,
                enlace_texto=_VER_EL_RESUMEN,
                enlace_ruta=_ruta_de_obra(
                    caso, carpeta_empresa, str(proyecto_id), _SECCION_RESUMEN
                ),
            )
        )
    return eventos
