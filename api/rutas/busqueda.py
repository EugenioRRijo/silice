"""`/v1/buscar`: búsquedas de solo lectura para los campos con autocompletado de la interfaz nueva
(diseño de autocompletado 2026-10-21 §5.1 y §5.4; Tarea 10 del plan de montar un presupuesto).

Por ahora una ruta, `GET /v1/buscar/partidas` (el buscador C-1 de partidas del catálogo); las demás
del diseño (insumos, unidades, línea base, proveedores) llegan con el plan de autocompletado.

- Acceso `LEER_PROYECTO` (arma y revisa, o clave de API); el administrador recibe 403.
- `Cache-Control: no-store` en toda respuesta, también en 401, 403, 422 y 503 (`RutaSinCache`
  envuelve a `RutaSinEco`, como en la Hoja).
- El 422 es un mensaje fijo que no repite lo buscado; un fallo de la base, un 503 sin SQL ni rutas.
- Opera sobre la carpeta de trabajo de la sesión (`SesionDep`); no hay parámetro de carpeta.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from api.acceso import LEER
from api.dependencias import SesionDep
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion.busqueda import (
    LARGO_MAXIMO,
    LIMITE_MAXIMO,
    LIMITE_POR_OMISION,
    buscar_partidas,
)
from core.catalog import Catalogo
from core.contracts.dominio import Dominio

MENSAJE_FORMA = (
    "La búsqueda no es válida: el texto admite hasta 80 caracteres, el dominio es civil, "
    "telecom, industrial o sistemas y el límite va de 1 a 50."
)
MENSAJE_BASE = "No se pudo leer el catálogo de la carpeta de trabajo."
ROTULO_PARTIDAS = "Partidas del catálogo"


class _RutaBusqueda(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño de la Hoja §1.3-7)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/buscar", tags=["busqueda"], route_class=_RutaBusqueda)


class PartidaHalladaRespuesta(BaseModel):
    clave: str = Field(description="Única en la lista: «partida:<código>»")
    codigo: str
    descripcion: str
    unidad: str
    dominio: str
    tiene_composicion: bool = Field(description="Tiene al menos una línea de composición")


class PartidasHalladasRespuesta(BaseModel):
    rotulo: str = Field(description="El rótulo del grupo en la lista")
    resultados: list[PartidaHalladaRespuesta]
    hay_mas: bool = Field(description="Quedaron coincidencias fuera de `limite`")


@router.get("/partidas", response_model=PartidasHalladasRespuesta, dependencies=LEER)
def partidas(
    sesion: SesionDep,
    q: Annotated[str, Query(max_length=LARGO_MAXIMO, description="Código o palabras")] = "",
    dominio: Dominio | None = None,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO)] = LIMITE_POR_OMISION,
) -> PartidasHalladasRespuesta:
    """Partidas del catálogo cuyo código o descripción tiene todas las palabras de `q`, por
    relevancia. Con menos de 2 letras responde vacío (no es un error)."""
    try:
        halladas, hay_mas = buscar_partidas(Catalogo(sesion), q, dominio, limite)
    except SQLAlchemyError:
        # El texto de un error de base lleva el SQL y sus parámetros: no sale por la API.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None
    return PartidasHalladasRespuesta(
        rotulo=ROTULO_PARTIDAS,
        resultados=[
            PartidaHalladaRespuesta(
                clave=f"partida:{partida.codigo}",
                codigo=partida.codigo,
                descripcion=partida.descripcion,
                unidad=partida.unidad,
                dominio=partida.dominio,
                tiene_composicion=partida.tiene_composicion,
            )
            for partida in halladas
        ],
        hay_mas=hay_mas,
    )
