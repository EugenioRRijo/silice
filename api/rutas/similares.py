"""`POST /v1/similares`: partidas parecidas del catalogo con su desglose (UC-03, RF-15 y RF-16).

Migracion de `ui/paginas/similares.py` (sesion 2b). La logica vive en `aplicacion.similares`;
aqui solo el esquema HTTP. Los montos y cantidades viajan ya formateados como texto. El acceso
(`editar_hoja`, clave o sesion) se declara en `api/main.py`. El caso es el que abre
`api.dependencias.sesion_api`: es el unico lugar que habria que cambiar cuando exista el caso por
sesion web (RM-2).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import SesionDep
from aplicacion.similares import ResultadoSimilares, proponer_similares

router = APIRouter(tags=["similares"])

MENSAJE_CATALOGO = "No se pudo leer el catálogo del caso abierto."


class SolicitudSimilares(BaseModel):
    descripcion: str


class LineaMaterialRespuesta(BaseModel):
    descripcion: str
    unidad: str
    cantidad: str
    precio: str


class LineaEquipoRespuesta(BaseModel):
    descripcion: str
    cantidad: str
    precio: str
    depreciacion: str


class LineaManoObraRespuesta(BaseModel):
    descripcion: str
    cantidad: str
    sueldo: str


class ComposicionRespuesta(BaseModel):
    unidad: str
    rendimiento: str
    materiales: list[LineaMaterialRespuesta]
    equipos: list[LineaEquipoRespuesta]
    mano_obra: list[LineaManoObraRespuesta]


class PropuestaRespuesta(BaseModel):
    codigo: str
    descripcion: str
    puntaje: str
    puntaje_corto: str
    composicion: ComposicionRespuesta | None
    aviso: str | None


class SimilaresRespuesta(BaseModel):
    propuestas: list[PropuestaRespuesta]
    falla: str | None
    mensaje: str | None


@router.post("/v1/similares", response_model=SimilaresRespuesta)
def proponer(cuerpo: SolicitudSimilares, sesion: SesionDep) -> ResultadoSimilares:
    """Las tres partidas mas parecidas a la descripcion, de mayor a menor similitud."""
    try:
        return proponer_similares(sesion, cuerpo.descripcion)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_CATALOGO) from None
