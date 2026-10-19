"""Administración, pestaña «Instalación» (UC-21; RF-98; spec S5 §5.2 y §6.5; RM-3 y RM-4).

Paridad con `ui/paginas/instalacion.py`, sobre `aplicacion.instalacion`:

- `GET /v1/admin/instalacion` → red local y API (de `silice.toml`; solo se leen: los cambios de
  red no se hacen desde el navegador), los juegos de respaldo, los eventos de seguridad perdidos sin
  revisar y si este equipo puede hacer operaciones sensibles.
- `POST /v1/admin/instalacion/respaldos` crea un juego de respaldo de la instalación y los casos.
- `GET /v1/admin/instalacion/respaldos/{nombre}` baja el juego en `.zip` (trae huellas de
  contraseñas y la clave de firma cifrada: solo desde el propio equipo, `no-store`).
- `POST /v1/admin/instalacion/eventos/{nombre}/revisar` marca un archivo como revisado.

Rol: `ADMINISTRAR_RED_Y_API`, solo con sesión. El `nombre` solo vale si es uno de los que lista la
pantalla (nunca se arma una ruta con lo que llega).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from api.admin_acceso import administrar, administrar_en_el_equipo
from api.rutas.admin_empresa import SensibleEstado
from aplicacion import instalacion as logica
from aplicacion.equipo import operacion_sensible_permitida
from operacion import base_datos, config, eventos_perdidos
from seguridad.permisos import Accion, Sensible
from seguridad.sesiones import SesionActiva

router = APIRouter(prefix="/v1/admin/instalacion", tags=["administracion"])
ADMIN = Depends(administrar(Accion.ADMINISTRAR_RED_Y_API))
EN_EL_EQUIPO = Depends(administrar_en_el_equipo(Sensible.CLAVE_DE_API))
SIN_CACHE = {"Cache-Control": "no-store"}
MENSAJE_SIN_JUEGO = "No hay un respaldo con ese nombre."
MENSAJE_SIN_EVENTO = "No hay un archivo de eventos perdidos pendiente con ese nombre."


class Juego(BaseModel):
    nombre: str
    motivo: str
    bases: int


class Pendiente(BaseModel):
    nombre: str
    diferencias: list[str]
    eventos: int


class InstalacionRespuesta(BaseModel):
    red_local: bool
    direccion: str
    puerto: int
    api_activa: bool
    puerto_api: int
    avisos: list[str]
    respaldos: list[Juego]
    pendientes: list[Pendiente]
    sensible: SensibleEstado


class RespaldoCreado(BaseModel):
    nombre: str


@router.get("", response_model=InstalacionRespuesta, dependencies=[ADMIN])
def ver(request: Request) -> InstalacionRespuesta:
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    ip = request.client.host if request.client else None
    permitida, motivo = operacion_sensible_permitida(ip)
    return InstalacionRespuesta(
        red_local=ajustes.red_local,
        direccion=ajustes.direccion,
        puerto=ajustes.puerto,
        api_activa=ajustes.api_activa,
        puerto_api=ajustes.puerto_api,
        avisos=list(ajustes.avisos),
        respaldos=[
            Juego(nombre=j.nombre, motivo=j.motivo, bases=j.bases)
            for j in logica.juegos_de_respaldo()
        ],
        pendientes=[
            Pendiente(nombre=e.nombre, diferencias=list(e.diferencias), eventos=e.eventos)
            for e in logica.eventos_sin_revisar()
        ],
        sensible=SensibleEstado(permitida=permitida, motivo=motivo),
    )


@router.post("/respaldos", response_model=RespaldoCreado, dependencies=[ADMIN])
def respaldar() -> RespaldoCreado:
    """Un juego manual de la instalación y de todos los casos (no se poda nunca)."""
    return RespaldoCreado(nombre=base_datos.respaldar_todo().name)


@router.get(
    "/respaldos/{nombre}",
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}}},
    dependencies=[EN_EL_EQUIPO],
)
def bajar(nombre: str) -> Response:
    juego = next((j for j in logica.juegos_de_respaldo() if j.nombre == nombre), None)
    if juego is None:
        raise HTTPException(status_code=404, detail=MENSAJE_SIN_JUEGO)
    return Response(
        content=logica.zip_del_juego(juego.carpeta),
        media_type="application/zip",
        headers={**SIN_CACHE, "Content-Disposition": f'attachment; filename="{juego.nombre}.zip"'},
    )


@router.post("/eventos/{nombre}/revisar", response_model=list[Pendiente])
def revisar(nombre: str, activa: Annotated[SesionActiva, ADMIN]) -> list[Pendiente]:
    """Marca el archivo como revisado (quien lo revisa consta por su login)."""
    evento = next((e for e in logica.eventos_sin_revisar() if e.nombre == nombre), None)
    if evento is None:
        raise HTTPException(status_code=404, detail=MENSAJE_SIN_EVENTO)
    eventos_perdidos.marcar_revisado(evento.archivo, por=activa.login)
    return [
        Pendiente(nombre=e.nombre, diferencias=list(e.diferencias), eventos=e.eventos)
        for e in logica.eventos_sin_revisar()
    ]
