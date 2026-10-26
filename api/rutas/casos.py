"""`/v1/casos`: el caso de la sesión del navegador (RM-2, ola 0a de la sesión 2b).

- `GET /v1/casos` → `{actual: {nombre, ruta_relativa}, casos: [{nombre, ruta_relativa}]}`: el caso
  de esta petición (`api.dependencias.url_de_la_peticion`) y los `.db` de la carpeta de casos
  (`operacion.base_datos.listar_casos`). Lo ve cualquier rol con sesión, y la clave de API (que ve
  el caso del proceso). **Ninguna ruta absoluta**: `ruta_relativa` es relativa a la carpeta de
  datos (`casos/obra.db`); un caso del proceso fuera de ella (un `APU_BASE` de otra carpeta) solo
  muestra su nombre.
- `POST /v1/casos/actual` `{nombre}` (CSRF y `Origin`; `CAMBIAR_CASO`, como «Cambiar de caso» del
  Inicio, `ui.caso.abrir_caso`): el nombre pasa por `resolver_caso` (sin `..`, rutas, unidades ni
  nombres reservados: 422) y debe estar en `listar_casos` (404). El caso se prepara con
  `preparar_base` al abrir su motor (503 si no se puede, y no queda elegido) y se guarda para la
  ficha (`api.caso_web`). Con la clave de API, 409: las integraciones trabajan en el caso del
  proceso (`APU_BASE`), que fija quien arranca la API. MOD-0: además se recuerda para la cuenta
  (`aplicacion.eleccion.recordar_caso`, en la transacción de la petición sobre la instalación), lo
  que olvida la obra recordada; `GET /v1/sesion` la restaura al volver a entrar.
- MOD-3a: `GET /v1/casos` agrega `empresa` (`{nombre, ruta_relativa}` de la carpeta del proceso, la
  de omisión de la instalación; `null` si el proceso no usa un archivo) y `es_demostracion` (la
  carpeta de esta petición es la de demostración). `DELETE /v1/casos/actual` (`CAMBIAR_CASO`,
  sesión, CSRF y `Origin`) es «Volver a la carpeta de la empresa»: la ficha olvida su carpeta y
  la cuenta recuerda `caso` nulo (que olvida la obra); 200 con la carpeta de la empresa, 409 con
  la clave de API, 503 si el proceso no usa un archivo o no se puede preparar.

Carpetas de trabajo (BCP-2; diseño de la bienvenida §4 y §9, rutas C0 a C3). La interfaz dice
«carpeta de trabajo»; la API sigue diciendo `caso`. Estas cuatro rutas responden con
`Cache-Control: no-store` y su 422 no repite lo enviado (`_RutaCarpetas`); la lógica está en
`aplicacion.casos`, aquí solo se traduce a HTTP:

- `GET /v1/casos/actual` (cualquier rol o la clave): el resumen de la carpeta de esta petición, en
  solo lectura y sin rutas absolutas (503 si el proceso no trabaja sobre un archivo).
- `POST /v1/casos` `{nombre}` (`CAMBIAR_CASO`): 201 con el nombre final saneado. No la abre (el
  front llama después a `POST /v1/casos/actual`). 409 si ya existe (sin distinguir mayúsculas), si
  se llegó al tope, si otra creación sigue en curso o con la clave; 422 por la forma o el nombre
  reservado; 503 si no se pudo preparar.
- `POST /v1/casos/subida` multipart `archivo` (uno) y `nombre` opcional (`CAMBIAR_CASO`): 201 con
  `aviso` si se migró con respaldo; 413 si pasa de 20 MiB; 422 si no es una carpeta de Sílice
  válida o es de una versión más nueva; 409 y 503 como al crear. Un rechazo no deja rastro.
- `POST /v1/casos/demostracion` (`EDITAR_HOJA`): 201 si la creó, 200 si ya estaba; la siembra un
  proceso hijo (`ejecutor_de_demostracion`, que las pruebas sustituyen); 503 si falla o si otra
  creación sigue en curso; 409 con la clave.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, StrictStr

from api import caso_web
from api.acceso import CUALQUIER_ROL
from api.dependencias import (
    SesionInstalacionDep,
    obtener_motor,
    ruta_de_url,
    url_de_la_peticion,
    url_de_ruta,
    url_del_proceso,
)
from api.rutas.sesion import Detalle
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import casos as carpetas
from aplicacion.eleccion import recordar_caso
from operacion import config, demostracion
from operacion.base_datos import (
    CasoYaExiste,
    ErrorDeBase,
    RutaDeCasoRechazada,
    listar_casos,
    resolver_caso,
)
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_NO_ESTA = "El caso «{nombre}» no está en la carpeta de casos: elija uno de la lista."
MENSAJE_CON_CLAVE = (
    "Con la clave de API se trabaja en el caso del proceso (APU_BASE); el caso se elige por "
    "sesión desde la interfaz."
)

FORMA_CREAR = "Escriba el nombre de la carpeta de trabajo como texto de hasta 200 caracteres."
FORMA_SUBIDA = (
    "Envíe un solo archivo .db en el campo «archivo» y, si quiere, un nombre de hasta 200 "
    "caracteres."
)
MENSAJE_SIN_ARCHIVO = (
    "Esta sesión no trabaja sobre un archivo de Sílice: no hay carpeta de trabajo que resumir."
)

router = APIRouter(prefix="/v1/casos", tags=["casos"])


class CasoRespuesta(BaseModel):
    nombre: str
    ruta_relativa: str


class CasosRespuesta(BaseModel):
    actual: CasoRespuesta | None = Field(
        description="El caso de esta sesión; `null` solo si el proceso no usa un archivo SQLite"
    )
    casos: list[CasoRespuesta]
    empresa: CasoRespuesta | None = Field(
        description="La carpeta de la empresa: la del proceso; `null` si no usa un archivo SQLite"
    )
    es_demostracion: bool = Field(description="Si la carpeta de esta sesión es la de demostración")


class EleccionCaso(BaseModel):
    nombre: str = Field(max_length=200, description="El nombre de un caso de la lista")


def _describir(ruta: Path) -> CasoRespuesta:
    """El nombre y la ruta relativa a la carpeta de datos; fuera de ella, solo el nombre."""
    try:
        relativa = ruta.resolve().relative_to(config.carpeta_datos().resolve()).as_posix()
    except ValueError:
        relativa = ruta.name
    return CasoRespuesta(nombre=ruta.name, ruta_relativa=relativa)


@router.get("", response_model=CasosRespuesta, dependencies=CUALQUIER_ROL)
def consultar_casos(request: Request) -> CasosRespuesta:
    """El caso de esta sesión y los de la carpeta de casos, por nombre. No abre ninguna base."""
    ruta = ruta_de_url(url_de_la_peticion(request))
    empresa = ruta_de_url(url_del_proceso())
    return CasosRespuesta(
        actual=None if ruta is None else _describir(ruta),
        casos=[_describir(caso) for caso in listar_casos()],
        empresa=None if empresa is None else _describir(empresa),
        es_demostracion=ruta is not None and carpetas.es_demostracion(ruta.name),
    )


@router.post(
    "/actual",
    response_model=CasoRespuesta,
    responses={
        403: {"model": Detalle, "description": "Sin `CAMBIAR_CASO`, o sin CSRF u origen propio."},
        404: {"model": Detalle, "description": "El caso no está en la carpeta de casos."},
        409: {"model": Detalle, "description": "Con la clave de API no se elige caso."},
        422: {"model": Detalle, "description": "El nombre lleva rutas, `..` o no es válido."},
        503: {"model": Detalle, "description": "El caso no se puede preparar (más nuevo...)."},
    },
)
def elegir_caso(
    datos: EleccionCaso,
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(Accion.CAMBIAR_CASO))],
    instalacion: SesionInstalacionDep,
) -> CasoRespuesta:
    """Fija el caso de esta ficha de sesión (lo olvida al salir o expirar) y lo recuerda para la
    cuenta (vuelve al entrar de nuevo)."""
    if activa is None:
        raise HTTPException(status_code=409, detail=MENSAJE_CON_CLAVE)
    try:
        ruta = resolver_caso(datos.nombre)
    except RutaDeCasoRechazada as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    if ruta not in {caso.resolve() for caso in listar_casos()}:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ESTA.format(nombre=ruta.name))
    obtener_motor(url_de_ruta(ruta))  # prepara la base una vez (503 si no se puede)
    recordar_caso(instalacion, activa.usuario_id, ruta.name, ahora())
    instalacion.commit()  # la ficha cambia solo si la instalación lo confirmó
    caso_web.fijar(activa.huella_ficha, ruta)
    return _describir(ruta)


@router.delete(
    "/actual",
    response_model=CasoRespuesta,
    responses={
        403: {"model": Detalle, "description": "Sin `CAMBIAR_CASO`, o sin CSRF u origen propio."},
        409: {"model": Detalle, "description": "Con la clave de API no se elige caso."},
        503: {"model": Detalle, "description": "El proceso no usa un archivo o no se prepara."},
    },
)
def volver_a_la_empresa(
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(Accion.CAMBIAR_CASO))],
    instalacion: SesionInstalacionDep,
) -> CasoRespuesta:
    """«Volver a la carpeta de la empresa»: la ficha deja de tener carpeta propia (trabaja en la
    del proceso) y la cuenta recuerda `caso` nulo, lo que olvida la obra recordada."""
    if activa is None:
        raise HTTPException(status_code=409, detail=MENSAJE_CON_CLAVE)
    url = url_del_proceso()
    empresa = ruta_de_url(url)
    if empresa is None:
        raise HTTPException(status_code=503, detail=MENSAJE_SIN_ARCHIVO)
    obtener_motor(url)  # prepara la base una vez (503 si no se puede)
    recordar_caso(instalacion, activa.usuario_id, None, ahora())
    instalacion.commit()  # la ficha cambia solo si la instalación lo confirmó
    caso_web.olvidar(activa.huella_ficha)
    return _describir(empresa)


# --- carpetas de trabajo (BCP-2: C0 a C3) ---------------------------------------------------------


class _RutaCarpetas(RutaSinCache, RutaSinEco):
    """`no-store` en toda respuesta y 422 sin eco; `RutaSinCache` envuelve a `RutaSinEco`."""


class NuevaCarpeta(BaseModel):
    nombre: StrictStr = Field(max_length=200, description="El nombre que escribió la persona")


class CasoSubido(CasoRespuesta):
    aviso: str | None = Field(description="Qué se hizo con el archivo (migrado con respaldo)")


class ResumenCarpeta(BaseModel):
    nombre: str
    ruta_relativa: str
    ubicacion: str = Field(description="Dónde está, en llano y sin ruta absoluta")
    partidas: int
    insumos: int
    lista_vigente: str | None
    proyectos: int
    proyectos_con_version: int
    es_demostracion: bool
    por_migrar: bool
    error: str | None


def ejecutor_de_demostracion() -> Callable[[Path], None]:
    """Quién siembra la demostración: el proceso hijo. Las pruebas lo sustituyen por un doble
    (`app.dependency_overrides`) para no correr `scripts/` en cada una."""
    return demostracion.construir


async def _un_solo_archivo(request: Request) -> None:
    """Un `archivo` repetido no se elige en silencio: es un 422 de forma (sin eco)."""
    formulario = await request.form()  # el que FastAPI ya leyó (queda en la petición)
    if len(formulario.getlist("archivo")) > 1:
        raise RequestValidationError(
            [{"type": "too_long", "loc": ("body", "archivo"), "msg": "un solo archivo"}]
        )


@contextmanager
def _traducir(*, demostracion_en_curso: int = 409) -> Iterator[None]:
    """Las excepciones de `aplicacion.casos` como estados HTTP, con su mensaje fijo."""
    try:
        yield
    except CasoYaExiste as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except RutaDeCasoRechazada as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except carpetas.TopeDeCarpetas as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except carpetas.CreacionEnCurso as error:
        raise HTTPException(status_code=demostracion_en_curso, detail=str(error)) from None
    except carpetas.ArchivoDemasiadoGrande as error:
        raise HTTPException(status_code=413, detail=str(error)) from None
    except (carpetas.ArchivoNoValido, carpetas.CarpetaMasNueva) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except (carpetas.PreparacionFallida, carpetas.DemostracionFallida) as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except ErrorDeBase:  # cualquier otro: sin su texto (puede traer rutas del servidor)
        raise HTTPException(status_code=503, detail=carpetas.MENSAJE_PREPARACION) from None


def resumen_actual(request: Request) -> ResumenCarpeta:
    """C0: el resumen de la carpeta de esta petición (la de la ficha o, con la clave, la del
    proceso), en solo lectura: no crea el archivo ni lo migra."""
    ruta = ruta_de_url(url_de_la_peticion(request))
    if ruta is None:
        raise HTTPException(status_code=503, detail=MENSAJE_SIN_ARCHIVO)
    resumen = carpetas.estado(ruta)
    return ResumenCarpeta(
        **_describir(ruta).model_dump(),
        ubicacion=resumen.ubicacion,
        partidas=resumen.partidas,
        insumos=resumen.insumos,
        lista_vigente=resumen.lista_vigente,
        proyectos=resumen.proyectos,
        proyectos_con_version=resumen.proyectos_con_version,
        es_demostracion=resumen.es_demostracion,
        por_migrar=resumen.por_migrar,
        error=resumen.error,
    )


@sin_eco(FORMA_CREAR)
def crear_carpeta(
    datos: NuevaCarpeta,
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(Accion.CAMBIAR_CASO))],
) -> CasoRespuesta:
    """C1: una carpeta de trabajo vacía con el nombre saneado. No la abre."""
    if activa is None:
        raise HTTPException(status_code=409, detail=MENSAJE_CON_CLAVE)
    with _traducir():
        ruta = carpetas.crear(datos.nombre)
    return _describir(ruta)


@sin_eco(FORMA_SUBIDA)
def subir_carpeta(
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(Accion.CAMBIAR_CASO))],
    _uno: Annotated[None, Depends(_un_solo_archivo)],
    archivo: Annotated[UploadFile, File(description="El `.db` de una carpeta de trabajo")],
    nombre: Annotated[str | None, Form(max_length=200)] = None,
) -> CasoSubido:
    """C2: un `.db` ajeno se valida, se respalda, se migra y solo entonces aparece; todo o nada."""
    if activa is None:
        raise HTTPException(status_code=409, detail=MENSAJE_CON_CLAVE)
    archivo.file.seek(0)
    with _traducir():
        subida = carpetas.subir_seguro(archivo.file, archivo.filename, nombre)
    return CasoSubido(**_describir(subida.ruta).model_dump(), aviso=subida.aviso)


def estrenar_demostracion(
    respuesta: Response,
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))],
    construir: Annotated[Callable[[Path], None], Depends(ejecutor_de_demostracion)],
) -> CasoRespuesta:
    """C3: la carpeta `demostracion.db`, ficticia; 201 si la creó, 200 si ya estaba. No la abre
    ni toca la carpeta abierta."""
    if activa is None:
        raise HTTPException(status_code=409, detail=MENSAJE_CON_CLAVE)
    with _traducir(demostracion_en_curso=503):
        ruta, creada = carpetas.demostracion(construir)
    if not creada:
        respuesta.status_code = 200
    return _describir(ruta)


_ERRORES_DE_CREACION = {
    403: {"model": Detalle, "description": "Sin el permiso, o sin CSRF u origen propio."},
    409: {"model": Detalle, "description": "Ya existe, tope, otra creación en curso o clave."},
    422: {"model": Detalle, "description": "Nombre con rutas, reservado o datos sin la forma."},
    503: {"model": Detalle, "description": "No se pudo preparar; nada quedó a medias."},
}
router.add_api_route(
    "/actual",
    resumen_actual,
    methods=["GET"],
    response_model=ResumenCarpeta,
    dependencies=CUALQUIER_ROL,
    responses={503: {"model": Detalle, "description": "El proceso no usa un archivo SQLite."}},
    route_class_override=_RutaCarpetas,
)
router.add_api_route(
    "",
    crear_carpeta,
    methods=["POST"],
    status_code=201,
    response_model=CasoRespuesta,
    responses=_ERRORES_DE_CREACION,
    route_class_override=_RutaCarpetas,
)
router.add_api_route(
    "/subida",
    subir_carpeta,
    methods=["POST"],
    status_code=201,
    response_model=CasoSubido,
    responses={
        **_ERRORES_DE_CREACION,
        413: {"model": Detalle, "description": "El archivo pasa de 20 MiB."},
        422: {"model": Detalle, "description": "No es una carpeta de Sílice válida o es nueva."},
    },
    route_class_override=_RutaCarpetas,
)
router.add_api_route(
    "/demostracion",
    estrenar_demostracion,
    methods=["POST"],
    status_code=201,
    response_model=CasoRespuesta,
    responses={
        200: {"model": CasoRespuesta, "description": "Ya existía con los datos de ejemplo."},
        403: {"model": Detalle, "description": "Sin `EDITAR_HOJA`, o sin CSRF u origen propio."},
        409: {"model": Detalle, "description": "Con la clave de API, o una demostración vacía."},
        503: {"model": Detalle, "description": "El proceso hijo falló o pasó su plazo."},
    },
    route_class_override=_RutaCarpetas,
)
