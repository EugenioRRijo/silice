"""Administración, pestaña «Asistente de IA» (S4 §3.1, §8.3, RV-15; T6 de la migración final).

Paridad con `pestana_asistente` de `ui/paginas/administracion.py`, sobre `asistente.administracion`
(la lógica y los textos de la pestaña viven allí una sola vez):

- `GET /v1/admin/asistente` → la configuración (activo, proveedor, modelos, dirección de Ollama y
  tope de costo como texto), los proveedores con su rótulo, la clave registrada **enmascarada**
  (sus 4 últimos caracteres), si hay una guardada sin cargar, si solo queda el respaldo cifrado, si
  falta el componente `ia` y si este equipo puede operar con la clave.
- `POST .../configuracion` guarda la configuración (apagar el asistente saca la clave de memoria).
- `POST .../clave` `{clave, contrasena_respaldo?}`, `POST .../clave/reactivar` `{contrasena}` y
  `POST .../clave/olvidar`: solo desde el propio equipo (`Sensible.CLAVE_DE_IA`).

Rol: `ADMINISTRAR_EMPRESA` (`ROL_DE_LO_SENSIBLE[Sensible.CLAVE_DE_IA]`, el mismo que la clásica),
solo con sesión. La clave y las contraseñas viajan solo en el cuerpo: no se guardan en otro sitio
que el almacén de credenciales (o su respaldo cifrado), no se registran y no vuelven en ninguna
respuesta ni en el 422 (`RutaSinEco`). Un intento fallido de reactivar deja un evento de seguridad
con quién y desde dónde, como la clásica. Ninguna ruta llama al proveedor de IA (sin gasto).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.admin_acceso import administrar, administrar_en_el_equipo, sin_cache
from api.sesion_web import ahora
from api.sin_eco import RutaSinEco as _RutaSinEco
from api.sin_eco import sin_eco as _sin_eco
from aplicacion.equipo import operacion_sensible_permitida
from asistente import administracion as ia
from asistente.clave import ClaveDeIA, ClaveNoRegistrable, RespaldoNoAbre, enmascarar
from asistente.configuracion import PROVEEDORES, leer
from asistente.instalacion import (
    EMPRESA_DE_LA_CLAVE,
    clave_de_la_instalacion,
    ruta_de_configuracion,
)
from operacion.instalacion import sesion_de_instalacion
from seguridad import eventos
from seguridad.permisos import Accion, Sensible
from seguridad.sesiones import SesionActiva

_registro = logging.getLogger(__name__)
MENSAJE_CONFIGURACION_INVALIDA = "Indique la configuración del asistente completa."
MENSAJE_CLAVE_INVALIDA = "Escriba la clave de IA como texto."
MENSAJE_CONTRASENA_INVALIDA = "Escriba la contraseña del respaldo como texto."
MENSAJE_PROVEEDOR = "Elija un proveedor de la lista."
#: Lo que `asistente` rechaza con un mensaje apto para mostrar (se enmascara por si trae la clave).
RECHAZOS = (ia.SinPermiso, ClaveNoRegistrable, ValueError)

router = APIRouter(
    prefix="/v1/admin/asistente",
    tags=["administracion"],
    dependencies=[Depends(sin_cache)],
    route_class=_RutaSinEco,
)
#: El rol lo comprueba la dependencia: quien pasa es administrador (`es_administrador=True` abajo).
ADMIN = Depends(administrar(Accion.ADMINISTRAR_EMPRESA))
EN_EL_EQUIPO = Depends(administrar_en_el_equipo(Sensible.CLAVE_DE_IA))


class Proveedor(BaseModel):
    valor: str
    etiqueta: str


class SensibleEstado(BaseModel):
    permitida: bool
    motivo: str


class AsistenteEstado(BaseModel):
    activo: bool
    proveedor: str
    proveedores: list[Proveedor]
    modelo_claude: str
    modelo_local: str
    anfitrion_ollama: str
    tope_usd: str
    clave_registrada: str | None
    clave_guardada: bool
    pide_contrasena: bool
    falta_el_componente: str | None
    aviso_de_nube: str
    sensible: SensibleEstado


class Resultado(BaseModel):
    mensaje: str
    estado: AsistenteEstado


class Configuracion(BaseModel):
    activo: bool
    proveedor: str
    modelo_claude: str
    modelo_local: str = ""
    anfitrion_ollama: str
    tope_usd: str


class NuevaClave(BaseModel):
    clave: str = Field(repr=False)
    contrasena_respaldo: str | None = Field(default=None, repr=False)


class Reactivacion(BaseModel):
    contrasena: str = Field(repr=False)


def _clave() -> ClaveDeIA | None:
    """La clave de IA de la instalación, o `None` si el extra `ia` (keyring) no está instalado."""
    try:
        return clave_de_la_instalacion()
    except ImportError:
        return None


def _exigir_clave() -> ClaveDeIA:
    clave = _clave()
    if clave is None:
        raise HTTPException(status_code=400, detail=ia.SIN_EXTRA_IA)
    return clave


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _estado(request: Request) -> AsistenteEstado:
    ruta, clave = ruta_de_configuracion(), _clave()
    if clave is None:
        vista = ia.VistaDeLaPestana(leer(ruta), None, False, False)
    else:
        vista = ia.vista_de_la_pestana(ruta, clave, EMPRESA_DE_LA_CLAVE)
    cfg = vista.configuracion
    permitida, motivo = operacion_sensible_permitida(_ip(request))
    return AsistenteEstado(
        activo=cfg.activo,
        proveedor=cfg.proveedor,
        proveedores=[
            Proveedor(valor=p, etiqueta=ia.ETIQUETAS_DE_PROVEEDOR.get(p, p)) for p in PROVEEDORES
        ],
        modelo_claude=cfg.modelo_claude,
        modelo_local=cfg.modelo_local,
        anfitrion_ollama=cfg.anfitrion_ollama,
        tope_usd=str(cfg.tope_usd),
        clave_registrada=vista.clave_registrada,
        clave_guardada=vista.clave_guardada,
        pide_contrasena=vista.pide_contrasena,
        falta_el_componente=None if clave is not None else ia.SIN_EXTRA_IA,
        aviso_de_nube=ia.AVISO_DE_NUBE,
        sensible=SensibleEstado(permitida=permitida, motivo=motivo),
    )


def _rechazo(error: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=enmascarar(str(error)))


@router.get("", response_model=AsistenteEstado, dependencies=[ADMIN])
def ver(request: Request) -> AsistenteEstado:
    return _estado(request)


@router.post("/configuracion", response_model=Resultado, dependencies=[ADMIN])
@_sin_eco(MENSAJE_CONFIGURACION_INVALIDA)
def configurar(datos: Configuracion, request: Request) -> Resultado:
    """Guarda la configuración; un tope no numérico o no positivo no toca el archivo."""
    if datos.proveedor not in PROVEEDORES:
        raise HTTPException(status_code=400, detail=MENSAJE_PROVEEDOR)
    try:
        ia.configurar(
            ruta_de_configuracion(),
            es_administrador=True,
            activo=datos.activo,
            proveedor=datos.proveedor,
            modelo_claude=datos.modelo_claude,
            modelo_local=datos.modelo_local,
            anfitrion_ollama=datos.anfitrion_ollama,
            tope_usd=datos.tope_usd,
            clave=_clave(),
        )
    except (ia.SinPermiso, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except OSError:
        raise HTTPException(status_code=503, detail=ia.CONFIGURACION_NO_GUARDADA) from None
    return Resultado(mensaje=ia.CONFIGURACION_GUARDADA, estado=_estado(request))


@router.post("/clave", response_model=Resultado, dependencies=[EN_EL_EQUIPO])
@_sin_eco(MENSAJE_CLAVE_INVALIDA)
def registrar(datos: NuevaClave, request: Request) -> Resultado:
    """Guarda la clave en el almacén de credenciales (o cifrada, si este no está)."""
    clave = _exigir_clave()
    try:
        mostrada = ia.registrar_clave(
            clave,
            EMPRESA_DE_LA_CLAVE,
            datos.clave,
            es_administrador=True,
            ip_cliente=_ip(request),
            contrasena_respaldo=datos.contrasena_respaldo or None,
        )
    except RECHAZOS as error:
        raise _rechazo(error) from None
    except OSError:
        raise HTTPException(status_code=503, detail=ia.CLAVE_NO_GUARDADA) from None
    return Resultado(mensaje=ia.clave_registrada_aviso(mostrada), estado=_estado(request))


def _anotar_reactivacion_fallida(activa: SesionActiva, ip: str | None) -> None:
    """Un evento de seguridad por intento fallido (S3 §7.4): quién y desde dónde, sin la
    contraseña ni la clave. Una base ocupada no tapa el aviso: se anota en el registro."""
    try:
        with sesion_de_instalacion() as bd:
            eventos.registrar(
                bd,
                ia.EVENTO_REACTIVAR_FALLIDA,
                ahora(),
                login=activa.login,
                ip=ip or "",
                detalle=ia.DETALLE_REACTIVAR_FALLIDA,
            )
            bd.commit()
    except Exception:  # noqa: BLE001 - como la clásica: el aviso al administrador va primero
        _registro.warning("No se pudo anotar el intento fallido de reactivar la clave de IA")


@router.post("/clave/reactivar", response_model=Resultado)
@_sin_eco(MENSAJE_CONTRASENA_INVALIDA)
def reactivar(
    datos: Reactivacion, request: Request, activa: Annotated[SesionActiva, EN_EL_EQUIPO]
) -> Resultado:
    """Trae la clave desde el respaldo cifrado con su contraseña; solo con el asistente activo."""
    clave = _exigir_clave()
    if not leer(ruta_de_configuracion()).activo:  # apagado, la clave no vuelve a la memoria
        raise HTTPException(status_code=400, detail=ia.APAGADO_NO_REACTIVA)
    ip = _ip(request)
    try:
        mostrada = ia.reactivar_clave(
            clave,
            EMPRESA_DE_LA_CLAVE,
            datos.contrasena,
            ruta=ruta_de_configuracion(),
            es_administrador=True,
            ip_cliente=ip,
        )
    except RespaldoNoAbre as error:
        _anotar_reactivacion_fallida(activa, ip)
        raise HTTPException(status_code=400, detail=str(error)) from None
    except RECHAZOS as error:
        raise _rechazo(error) from None
    except OSError:
        raise HTTPException(status_code=503, detail=ia.RESPALDO_NO_LEIDO) from None
    return Resultado(mensaje=ia.clave_reactivada_aviso(mostrada), estado=_estado(request))


@router.post("/clave/olvidar", response_model=Resultado, dependencies=[EN_EL_EQUIPO])
def olvidar(request: Request) -> Resultado:
    """Borra la clave del almacén, del respaldo y de la memoria."""
    clave = _exigir_clave()
    try:
        ia.olvidar_clave(clave, EMPRESA_DE_LA_CLAVE, es_administrador=True)
    except ia.SinPermiso as error:
        raise _rechazo(error) from None
    return Resultado(mensaje=ia.CLAVE_OLVIDADA, estado=_estado(request))
