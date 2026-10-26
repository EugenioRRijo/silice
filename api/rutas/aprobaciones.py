"""`/v1/aprobaciones`: el ciclo de aprobación de una versión (MP-4, Tarea 18 del plan de montar un
presupuesto, con los cambios por el diseño de módulos; diseño §5.4 y §10).

Rutas finas sobre `aplicacion.aprobaciones` (la regla y el rastro, en la carpeta de trabajo) y
`aplicacion.indice_aprobaciones` (el reflejo de todas las carpetas en `instalacion.db`):

- `POST ""` (`editar_hoja`) `{proyecto, version, nota}` → 201 `{id, estado, retirada}`.
- `GET ""?proyecto=` (`editar_hoja`) → `{rastro: {integro, mensaje}, fases, versiones: {código:
  {estado, por, el, notas, armo}}, eventos: [...]}` de la obra en la carpeta de la sesión.
- `GET /pendientes` (`aprobar_version`) → las filas del índice en aprobación, de todas las carpetas,
  lo más antiguo primero; antes vuelve a reflejar la carpeta abierta (la repone si se perdió).
- `GET /mias` (`editar_hoja`, solo con sesión) → las 20 últimas filas que envió la cuenta.
- `GET /resumen` (`aprobar_version`) → la cifra «Por aprobar» de la mesa, con la forma de las
  cifras de `GET /v1/obras/resumen`: cuántas esperan dictamen y los días hábiles de la más antigua
  (`aplicacion.mesa.dias_habiles_entre`), marcada desde 3.
- `POST /abrir` (`aprobar_version`, solo con sesión) `{caso, envio_id}` → `{caso}`: cambia la
  carpeta de la sesión a la del envío (`caso_web.fijar`) y la recuerda para la cuenta
  (`aplicacion.eleccion.recordar_caso`, MOD-0); así llega quien revisa sin `cambiar_caso`
  (decisión 1 ratificada). 404 «No se encontró ese envío.» si la carpeta no está en la carpeta de
  casos (o el nombre trae rutas) o no tiene ese envío; la sesión no cambia.
- `GET /{envio_id}` (`aprobar_version`) → lo que se aprueba, en solo lectura: los renglones y los
  hallazgos GUARDADOS de la versión (lo que su sello cubre), el total, el rastro de la obra, quién
  envió y si quien mira la armó. No abre borrador ni registra instantánea.
- `POST /{envio_id}/dictamen` (`aprobar_version`, solo con sesión) `{resultado, notas}` → 201
  `{id, estado}`.

Las que escriben en la carpeta usan la sesión de escritura (`BEGIN IMMEDIATE`, SL-E12): dos
dictámenes a la vez se ordenan y el segundo recibe «Este envío ya tiene dictamen o fue retirado.».
Después de confirmar la carpeta se refleja el índice y se confirma la instalación; si eso falla, la
respuesta no cambia (lo que vale es la carpeta) y el próximo `GET /pendientes` lo repone.

Errores: `NoSeEncontro` → 404, `DatosInvalidos` → 422, otra `AprobacionInvalida` → 409, con su
mensaje; el 422 de forma es un mensaje fijo que no repite lo enviado; un fallo de la base, 503 sin
SQL ni rutas; con la clave de API, 403 en lo que es de una cuenta. `Cache-Control: no-store` en
toda respuesta. Montos como texto. La interfaz dice «obra»; la API conserva `proyecto`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, StrictInt, StrictStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api import caso_web
from api.dependencias import (
    USUARIO_API,
    SesionDeEscrituraDep,
    SesionDep,
    SesionInstalacionDep,
    obtener_motor,
    ruta_de_url,
    url_de_la_peticion,
    url_de_ruta,
    url_del_proceso,
)
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion import aprobaciones, indice_aprobaciones
from aplicacion.aprobaciones import (
    AprobacionInvalida,
    DatosInvalidos,
    EnvioRegistrado,
    NoSeEncontro,
)
from aplicacion.eleccion import recordar_caso
from aplicacion.indice_aprobaciones import FilaIndice
from aplicacion.mesa import dias_habiles_entre
from core.catalog import abrir_sesion
from operacion.base_datos import RutaDeCasoRechazada, listar_casos, resolver_caso
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = (
    "Revise lo enviado: la obra y la versión van como texto, el dictamen es aprobada, aprobada "
    "con observaciones o devuelta, y las notas admiten hasta 2000 caracteres."
)
MENSAJE_BASE = "No se pudo leer o guardar la aprobación en la carpeta de trabajo."
MENSAJE_CON_CLAVE = "Esta acción se hace entrando con su cuenta, no con la clave de API."
#: Desde cuántos días hábiles de espera la cifra «Por aprobar» se marca.
DIAS_PARA_MARCAR = 3

_registro = logging.getLogger(__name__)


class _RutaAprobaciones(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (como en la Hoja)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/aprobaciones", tags=["aprobaciones"], route_class=_RutaAprobaciones)
EDITAR = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))
APROBAR = Depends(exigir_clave_o_sesion(Accion.APROBAR_VERSION))
CuentaQueEdita = Annotated[SesionActiva | None, EDITAR]
CuentaQueAprueba = Annotated[SesionActiva | None, APROBAR]


# --- esquemas -------------------------------------------------------------------------------------


class AprobacionEnvioPeticion(BaseModel):
    proyecto: StrictStr = Field(max_length=200, description="El código o el nombre de la obra")
    version: StrictStr = Field(max_length=40, description="El código de la versión guardada")
    nota: StrictStr = Field(default="", max_length=2000, description="Nota opcional del envío")


class AprobacionEnvioRespuesta(BaseModel):
    id: int
    estado: str
    retirada: str | None = Field(description="La versión pendiente que este envío retiró")


class AprobacionDictamenPeticion(BaseModel):
    resultado: Literal["aprobada", "aprobada_con_observaciones", "devuelta"]
    notas: StrictStr = Field(
        default="",
        max_length=2000,
        description="Obligatorias para devolver o aprobar con observaciones",
    )


class AprobacionDictamenRespuesta(BaseModel):
    id: int
    estado: str


class AprobacionAbrirPeticion(BaseModel):
    caso: StrictStr = Field(max_length=255, description="La carpeta del envío (`caso` del índice)")
    envio_id: StrictInt


class AprobacionAbrirRespuesta(BaseModel):
    caso: str


class AprobacionRastroRespuesta(BaseModel):
    integro: bool
    mensaje: str


class AprobacionEstadoRespuesta(BaseModel):
    estado: str
    por: str | None
    el: datetime | None
    notas: str
    armo: bool


class AprobacionEventoRespuesta(BaseModel):
    id: int
    tipo: str
    version: str
    resultado: str | None
    notas: str
    por: str
    el: datetime
    armo: bool
    cierre_de: int | None


class AprobacionObraRespuesta(BaseModel):
    rastro: AprobacionRastroRespuesta
    fases: str = Field(description="«VIV-001 devuelta → VIV-002 aprobada»")
    versiones: dict[str, AprobacionEstadoRespuesta]
    eventos: list[AprobacionEventoRespuesta]


class AprobacionFilaRespuesta(BaseModel):
    caso: str
    envio_id: int
    proyecto: str = Field(description="El código de la obra en su carpeta")
    obra: str
    version: str
    total: str
    moneda: str
    estado: str
    enviado_por: str
    enviado_el: datetime
    dictamen_por: str | None
    dictamen_el: datetime | None
    nota: str = Field(description="La nota del envío")
    notas: str = Field(description="Las notas del dictamen")
    armo: bool = Field(description="Quien dictaminó es quien guardó la versión")


class AprobacionCifraRespuesta(BaseModel):
    clave: str
    titulo: str
    actual: str
    meta: str
    delta: str
    delta_pct: str | None
    sentido: str
    detalle: str | None
    marcada: bool


class AprobacionPartidaRespuesta(BaseModel):
    codigo: str
    descripcion: str
    unidad: str
    cantidad: str
    precio_unitario: str | None = Field(description="`null` en un ítem pendiente")
    total: str | None
    pendiente: bool = Field(description="Ítem sin partida en el catálogo: sin precio")


class AprobacionHallazgoRespuesta(BaseModel):
    regla: str
    severidad: str
    descripcion: str


class AprobacionHallazgosRespuesta(BaseModel):
    error: int = Field(description="Los de severidad error o crítica")
    advertencia: int
    info: int
    lista: list[AprobacionHallazgoRespuesta]


class AprobacionCadenaRespuesta(BaseModel):
    integra: bool
    mensaje: str = Field(description="El mismo texto de la pestaña Trazabilidad")


class AprobacionEnvioDeLaVersion(BaseModel):
    por: str
    el: datetime
    nota: str


class AprobacionDetalleRespuesta(BaseModel):
    envio_id: int
    proyecto: str
    obra: str
    version: str
    estado: str
    moneda: str
    total: str
    partidas: list[AprobacionPartidaRespuesta]
    hallazgos: AprobacionHallazgosRespuesta
    rastro: AprobacionRastroRespuesta
    cadena: AprobacionCadenaRespuesta = Field(
        description="La cadena de versiones recalculada: si no está íntegra, no se dictamina"
    )
    envio: AprobacionEnvioDeLaVersion
    armo: bool = Field(description="Quien mira es quien guardó la versión")


# --- ayudantes ------------------------------------------------------------------------------------


def _texto(valor: Decimal) -> str:
    return format(valor, "f")


def _http(error: AprobacionInvalida) -> HTTPException:
    if isinstance(error, NoSeEncontro):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, DatosInvalidos):
        return HTTPException(422, str(error))
    return HTTPException(status.HTTP_409_CONFLICT, str(error))


def _sin_base() -> HTTPException:
    # El texto de un error de base lleva el SQL y sus parámetros: no sale por la API.
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE)


def _con_cuenta(activa: SesionActiva | None) -> SesionActiva:
    if activa is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, MENSAJE_CON_CLAVE)
    return activa


def _caso(request: Request) -> str | None:
    """El nombre del archivo de la carpeta de esta petición (`None` si no es un archivo)."""
    ruta = ruta_de_url(url_de_la_peticion(request))
    return None if ruta is None else ruta.name


def _reflejar(instalacion: Session, caso: str | None, sesion: Session) -> None:
    """Reescribe en el índice las filas de la carpeta y confirma la instalación. Un fallo no
    cambia la respuesta: la carpeta ya está confirmada y es la que manda."""
    if caso is None:
        return
    try:
        indice_aprobaciones.reflejar(instalacion, caso, sesion)
        instalacion.commit()
    except Exception:  # noqa: BLE001 (la carpeta ya confirmó: ningún fallo aquí la desdice)
        instalacion.rollback()
        _registro.warning(
            "No se pudo reflejar el índice de aprobaciones de %s.", caso, exc_info=True
        )
    finally:
        sesion.rollback()  # suelta la carpeta: la lectura del reflejo no deja nada abierto


def _fila(fila: FilaIndice) -> AprobacionFilaRespuesta:
    return AprobacionFilaRespuesta(
        caso=fila.caso,
        envio_id=fila.envio_id,
        proyecto=fila.proyecto,
        obra=fila.obra,
        version=fila.version,
        total=_texto(fila.total),
        moneda=fila.moneda,
        estado=fila.estado,
        enviado_por=fila.enviado_por,
        enviado_el=fila.enviado_el,
        dictamen_por=fila.dictamen_por,
        dictamen_el=fila.dictamen_el,
        nota=fila.nota,
        notas=fila.notas,
        armo=fila.armo,
    )


def _carpeta(caso: str) -> Path | None:
    """La carpeta `caso`: la de la empresa (la del proceso) o una de la carpeta de casos; `None`
    si no es ninguna (también si el nombre trae rutas o `..`)."""
    empresa = ruta_de_url(url_del_proceso())
    if empresa is not None and caso == empresa.name:
        return empresa
    try:
        ruta = resolver_caso(caso)
    except RutaDeCasoRechazada:
        return None
    return ruta if ruta in {c.resolve() for c in listar_casos()} else None


def _es_la_de_la_empresa(ruta: Path) -> bool:
    empresa = ruta_de_url(url_del_proceso())
    return empresa is not None and ruta.resolve() == empresa.resolve()


def _dias(n: int) -> str:
    return f"{n} {'día hábil' if n == 1 else 'días hábiles'}"


# --- rutas ----------------------------------------------------------------------------------------


@router.post("", response_model=AprobacionEnvioRespuesta, status_code=201, dependencies=[EDITAR])
def enviar(
    peticion: AprobacionEnvioPeticion,
    request: Request,
    activa: CuentaQueEdita,
    sesion: SesionDeEscrituraDep,
    instalacion: SesionInstalacionDep,
) -> AprobacionEnvioRespuesta:
    """Envía una versión guardada a aprobación (retira la pendiente de la obra, si había)."""
    try:
        envio = aprobaciones.enviar(
            sesion,
            peticion.proyecto,
            peticion.version,
            nota=peticion.nota,
            usuario=USUARIO_API if activa is None else activa.usuario,
            ahora=ahora(),
        )
    except AprobacionInvalida as error:
        raise _http(error) from None
    except SQLAlchemyError:
        raise _sin_base() from None
    _reflejar(instalacion, _caso(request), sesion)
    return AprobacionEnvioRespuesta(id=envio.id, estado="en_aprobacion", retirada=envio.retirada)


@router.get("", response_model=AprobacionObraRespuesta, dependencies=[EDITAR])
def consultar_obra(
    activa: CuentaQueEdita,
    sesion: SesionDep,
    proyecto: Annotated[str, Query(max_length=200, description="Código o nombre de la obra")],
) -> AprobacionObraRespuesta:
    """El rastro de aprobaciones de la obra, sus fases, el estado de cada versión y sus eventos."""
    del activa  # el acceso ya se comprobó
    try:
        rastro = aprobaciones.verificar_rastro(sesion, proyecto)
        fases = aprobaciones.fases(sesion, proyecto)
        estados = aprobaciones.estados(sesion, proyecto)
        eventos = aprobaciones.historial(sesion, proyecto)
    except AprobacionInvalida as error:
        raise _http(error) from None
    except SQLAlchemyError:
        raise _sin_base() from None
    return AprobacionObraRespuesta(
        rastro=AprobacionRastroRespuesta(integro=rastro.integro, mensaje=rastro.mensaje),
        fases=fases,
        versiones={
            codigo: AprobacionEstadoRespuesta(
                estado=e.estado, por=e.por, el=e.el, notas=e.notas, armo=e.armo
            )
            for codigo, e in estados.items()
        },
        eventos=[
            AprobacionEventoRespuesta(
                id=e.id,
                tipo=e.tipo,
                version=e.version,
                resultado=e.resultado,
                notas=e.notas,
                por=e.usuario,
                el=e.fecha_hora,
                armo=e.armo,
                cierre_de=e.cierre_de,
            )
            for e in eventos
        ],
    )


@router.get("/pendientes", response_model=list[AprobacionFilaRespuesta], dependencies=[APROBAR])
def por_aprobar(
    request: Request,
    activa: CuentaQueAprueba,
    sesion: SesionDep,
    instalacion: SesionInstalacionDep,
) -> list[AprobacionFilaRespuesta]:
    """Lo que espera dictamen en todas las carpetas, lo más antiguo primero."""
    del activa
    _reflejar(instalacion, _caso(request), sesion)
    try:
        return [_fila(f) for f in indice_aprobaciones.pendientes(instalacion)]
    except SQLAlchemyError:
        raise _sin_base() from None


@router.get("/mias", response_model=list[AprobacionFilaRespuesta], dependencies=[EDITAR])
def mias(
    request: Request,
    activa: CuentaQueEdita,
    sesion: SesionDep,
    instalacion: SesionInstalacionDep,
) -> list[AprobacionFilaRespuesta]:
    """Las últimas 20 versiones que la cuenta envió a aprobación, con su dictamen."""
    cuenta = _con_cuenta(activa)
    _reflejar(instalacion, _caso(request), sesion)
    try:
        return [_fila(f) for f in indice_aprobaciones.de_quien(instalacion, cuenta.usuario)]
    except SQLAlchemyError:
        raise _sin_base() from None


@router.get("/resumen", response_model=AprobacionCifraRespuesta, dependencies=[APROBAR])
def resumen(
    request: Request,
    activa: CuentaQueAprueba,
    sesion: SesionDep,
    instalacion: SesionInstalacionDep,
) -> AprobacionCifraRespuesta:
    """La cifra «Por aprobar»: cuántas versiones esperan dictamen y cuánto lleva la más antigua."""
    del activa
    _reflejar(instalacion, _caso(request), sesion)
    try:
        filas = indice_aprobaciones.pendientes(instalacion)
    except SQLAlchemyError:
        raise _sin_base() from None
    dias = 0 if not filas else dias_habiles_entre(filas[0].enviado_el.date(), ahora().date())
    return AprobacionCifraRespuesta(
        clave="por_aprobar",
        titulo="Por aprobar",
        actual=str(len(filas)),
        meta="0",
        delta=str(dias),
        delta_pct=None,
        sentido="costo",
        detalle=None
        if not filas
        else f"La más antigua: {filas[0].obra} {filas[0].version}, {_dias(dias)}",
        marcada=bool(filas) and dias >= DIAS_PARA_MARCAR,
    )


@router.post("/abrir", response_model=AprobacionAbrirRespuesta, dependencies=[APROBAR])
def abrir(
    peticion: AprobacionAbrirPeticion,
    activa: CuentaQueAprueba,
    instalacion: SesionInstalacionDep,
) -> AprobacionAbrirRespuesta:
    """Cambia la carpeta de esta sesión a la del envío y la recuerda para la cuenta."""
    cuenta = _con_cuenta(activa)
    ruta = _carpeta(peticion.caso)
    if ruta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, aprobaciones.SIN_ENVIO)
    motor = obtener_motor(url_de_ruta(ruta))  # prepara la carpeta una vez (503 si no se puede)
    try:
        with abrir_sesion(motor) as sesion_caso:
            aprobaciones.envio(sesion_caso, peticion.envio_id)
        empresa = _es_la_de_la_empresa(ruta)
        recordar_caso(instalacion, cuenta.usuario_id, None if empresa else ruta.name, ahora())
        instalacion.commit()  # la ficha cambia solo si la instalación lo confirmó
    except AprobacionInvalida as error:
        raise _http(error) from None
    except SQLAlchemyError:
        raise _sin_base() from None
    if empresa:
        caso_web.olvidar(cuenta.huella_ficha)
    else:
        caso_web.fijar(cuenta.huella_ficha, ruta)
    return AprobacionAbrirRespuesta(caso=ruta.name)


@router.get("/{envio_id}", response_model=AprobacionDetalleRespuesta, dependencies=[APROBAR])
def detalle(
    envio_id: int, activa: CuentaQueAprueba, sesion: SesionDep
) -> AprobacionDetalleRespuesta:
    """Lo que se aprueba, en solo lectura, con su rastro y quién la envió."""
    try:
        leido = aprobaciones.detalle_de_envio(
            sesion, envio_id, USUARIO_API if activa is None else activa.usuario
        )
    except AprobacionInvalida as error:
        raise _http(error) from None
    except SQLAlchemyError:
        raise _sin_base() from None
    enviado: EnvioRegistrado = leido.envio
    severidades = [h.severidad for h in leido.hallazgos]
    return AprobacionDetalleRespuesta(
        envio_id=enviado.id,
        proyecto=leido.proyecto,
        obra=leido.obra,
        version=enviado.version,
        estado=enviado.estado,
        moneda=leido.moneda,
        total=_texto(leido.total),
        partidas=[
            AprobacionPartidaRespuesta(
                codigo=p.codigo,
                descripcion=p.descripcion,
                unidad=p.unidad,
                cantidad=_texto(p.cantidad),
                precio_unitario=None if p.precio_unitario is None else _texto(p.precio_unitario),
                total=None if p.total is None else _texto(p.total),
                pendiente=p.pendiente,
            )
            for p in leido.partidas
        ],
        hallazgos=AprobacionHallazgosRespuesta(
            error=sum(1 for s in severidades if s in ("error", "critico")),
            advertencia=severidades.count("advertencia"),
            info=severidades.count("info"),
            lista=[
                AprobacionHallazgoRespuesta(
                    regla=h.regla, severidad=h.severidad, descripcion=h.descripcion
                )
                for h in leido.hallazgos
            ],
        ),
        rastro=AprobacionRastroRespuesta(
            integro=leido.rastro.integro, mensaje=leido.rastro.mensaje
        ),
        cadena=AprobacionCadenaRespuesta(
            integra=leido.cadena.integra, mensaje=leido.cadena.mensaje
        ),
        envio=AprobacionEnvioDeLaVersion(por=enviado.por, el=enviado.el, nota=enviado.nota),
        armo=leido.armo,
    )


@router.post(
    "/{envio_id}/dictamen",
    response_model=AprobacionDictamenRespuesta,
    status_code=201,
    dependencies=[APROBAR],
)
def dictaminar(
    envio_id: int,
    peticion: AprobacionDictamenPeticion,
    request: Request,
    activa: CuentaQueAprueba,
    sesion: SesionDeEscrituraDep,
    instalacion: SesionInstalacionDep,
) -> AprobacionDictamenRespuesta:
    """Registra el dictamen sobre el envío (solo con la cuenta de una persona)."""
    cuenta = _con_cuenta(activa)
    try:
        evento = aprobaciones.dictaminar(
            sesion,
            envio_id,
            resultado=peticion.resultado,
            notas=peticion.notas,
            usuario=cuenta.usuario,
            ahora=ahora(),
        )
    except AprobacionInvalida as error:
        raise _http(error) from None
    except SQLAlchemyError:
        raise _sin_base() from None
    _reflejar(instalacion, _caso(request), sesion)
    return AprobacionDictamenRespuesta(id=evento, estado=peticion.resultado)
