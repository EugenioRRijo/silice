"""Administración, pestaña «Empresa y clave de firma» (UC-21; RF-80, RF-84; RM-3 y RM-4).

Paridad con `_pestana_empresa` de `ui/paginas/administracion.py`, sobre `seguridad.empresas`:

- `GET /v1/admin/empresa` → `{empresa, clave, sensible}`; `sensible` dice si este equipo puede
  operar con la clave (`aplicacion.equipo`) y, si no, por qué.
- `POST /v1/admin/empresa` `{nombre, rif, ciudad}` guarda la empresa.
- `POST /v1/admin/empresa/clave` `{contrasena}` genera la clave de firma (solo en el propio equipo).
- `GET /v1/admin/empresa/clave-publica` y `GET /v1/admin/empresa/respaldo-clave` (esta, solo en el
  propio equipo y cifrada: nunca sale la privada en claro).
- `POST /v1/admin/empresa/clave/retirar` `{motivo?}` y `.../revocar` `{motivo, contrasena?}`: la
  privada se destruye; con la contraseña, `revocar` devuelve el aviso firmado en base64.

Rol: `ADMINISTRAR_EMPRESA`, solo con sesión. Las contraseñas no se guardan, no se registran y no
vuelven en ningún cuerpo (el 422 no repite lo enviado). Con contraseñas equivocadas se comparte el
freno de la clave de firma (`entregas.FRENO_FIRMA`).
"""

from __future__ import annotations

import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api.admin_acceso import administrar, administrar_en_el_equipo
from api.rutas.entregas import FRENO_FIRMA, MENSAJE_FRENO
from api.rutas.sesion import _RutaSinEco, _sin_eco
from api.sesion_web import ahora
from aplicacion.equipo import operacion_sensible_permitida
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, empresas, firma
from seguridad.permisos import Accion, Sensible
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = "Indique los datos como texto."
MENSAJE_SIN_MOTIVO = "Escriba el motivo de la revocación."
SIN_CACHE = {"Cache-Control": "no-store"}
ERRORES_ESPERADOS = (empresas.ClaveError, cuentas.ContrasenaInvalida, LookupError, ValueError)

router = APIRouter(prefix="/v1/admin/empresa", tags=["administracion"], route_class=_RutaSinEco)
ADMIN = Depends(administrar(Accion.ADMINISTRAR_EMPRESA))
EN_EL_EQUIPO = Depends(administrar_en_el_equipo(Sensible.CLAVE_DE_FIRMA))


class EmpresaDatos(BaseModel):
    nombre: str
    rif: str
    ciudad: str = ""


class ClaveDatos(BaseModel):
    estado: str
    huella: str


class SensibleEstado(BaseModel):
    permitida: bool
    motivo: str


class EmpresaRespuesta(BaseModel):
    empresa: EmpresaDatos | None
    clave: ClaveDatos | None
    sensible: SensibleEstado


class GenerarClave(BaseModel):
    contrasena: str = Field(repr=False)


class BajaDeClave(BaseModel):
    motivo: str = ""
    contrasena: str | None = Field(default=None, repr=False)


class AvisoRespuesta(BaseModel):
    #: El aviso de revocación firmado (base64); `None` si no hubo contraseña.
    aviso: str | None


def _estado(request: Request) -> EmpresaRespuesta:
    ip = request.client.host if request.client else None
    permitida, motivo = operacion_sensible_permitida(ip)
    with sesion_de_instalacion() as bd:
        propia = empresas.empresa_propia(bd)
        activa = empresas.clave_activa(bd)
        return EmpresaRespuesta(
            empresa=(
                EmpresaDatos(nombre=propia.nombre, rif=propia.rif, ciudad=propia.ciudad)
                if propia is not None
                else None
            ),
            clave=(
                ClaveDatos(estado=activa.estado, huella=firma.huella_corta(activa.publica))
                if activa is not None
                else None
            ),
            sensible=SensibleEstado(permitida=permitida, motivo=motivo),
        )


def _rechazo(error: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


@router.get("", response_model=EmpresaRespuesta, dependencies=[ADMIN])
def ver(request: Request) -> EmpresaRespuesta:
    """La empresa, la huella de su clave activa y si este equipo puede operar con ella."""
    return _estado(request)


@router.post("", response_model=EmpresaRespuesta)
@_sin_eco(MENSAJE_CUERPO_INVALIDO)
def guardar(
    datos: EmpresaDatos, request: Request, activa: Annotated[SesionActiva, ADMIN]
) -> EmpresaRespuesta:
    with sesion_de_instalacion() as bd:
        try:
            empresas.guardar_empresa_propia(
                bd, datos.nombre, datos.rif, datos.ciudad, activa.login, ahora()
            )
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _estado(request)


@router.post("/clave", response_model=EmpresaRespuesta)
@_sin_eco(MENSAJE_CUERPO_INVALIDO)
def generar(
    datos: GenerarClave, request: Request, activa: Annotated[SesionActiva, EN_EL_EQUIPO]
) -> EmpresaRespuesta:
    """Genera el par de claves en este equipo; la privada queda cifrada con la contraseña."""
    with sesion_de_instalacion() as bd:
        try:
            empresas.generar_clave(bd, datos.contrasena, activa.login, ahora())
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _estado(request)


@router.get(
    "/clave-publica",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
    dependencies=[ADMIN],
)
def clave_publica() -> Response:
    with sesion_de_instalacion() as bd:
        try:
            datos = empresas.exportar_clave_publica_propia(bd, ahora())
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _descarga(datos, "clave-publica.silice-clave")


@router.get(
    "/respaldo-clave",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
    dependencies=[EN_EL_EQUIPO],
)
def respaldo_de_la_clave() -> Response:
    """La clave activa tal como está guardada (cifrada), para un respaldo aparte."""
    with sesion_de_instalacion() as bd:
        try:
            datos = empresas.exportar_respaldo_cifrado(bd)
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _descarga(datos, "respaldo-clave.silice-respaldo")


def _descarga(datos: bytes, nombre: str) -> Response:
    return Response(
        content=datos,
        media_type="application/octet-stream",
        headers={**SIN_CACHE, "Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/clave/retirar", response_model=EmpresaRespuesta)
@_sin_eco(MENSAJE_CUERPO_INVALIDO)
def retirar(
    datos: BajaDeClave, request: Request, activa: Annotated[SesionActiva, EN_EL_EQUIPO]
) -> EmpresaRespuesta:
    """Cambio de clave sin compromiso: se destruye la privada de este equipo."""
    with sesion_de_instalacion() as bd:
        try:
            empresas.retirar_clave(bd, activa.login, ahora(), datos.motivo)
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return _estado(request)


@router.post("/clave/revocar", response_model=AvisoRespuesta)
@_sin_eco(MENSAJE_CUERPO_INVALIDO)
def revocar(datos: BajaDeClave, activa: Annotated[SesionActiva, EN_EL_EQUIPO]) -> AvisoRespuesta:
    """Clave perdida o expuesta: los paquetes firmados con ella dejan de verificar."""
    if datos.motivo.strip() == "":
        raise HTTPException(status_code=400, detail=MENSAJE_SIN_MOTIVO)
    momento = ahora()
    if datos.contrasena:
        espera = FRENO_FIRMA.espera(momento)
        if espera > 0:
            raise HTTPException(
                status_code=429, detail=MENSAJE_FRENO, headers={"Retry-After": str(int(espera) + 1)}
            )
    with sesion_de_instalacion() as bd:
        try:
            aviso = empresas.revocar_clave_propia(
                bd, activa.login, momento, datos.motivo, datos.contrasena or None
            )
        except empresas.ContrasenaDeClaveIncorrecta as error:
            FRENO_FIRMA.registrar_fallo(momento)
            raise _rechazo(error) from None
        except ERRORES_ESPERADOS as error:
            raise _rechazo(error) from None
    return AvisoRespuesta(aviso=base64.b64encode(aviso).decode("ascii") if aviso else None)
