"""`/v1/consulta/{tabla}`: autocompletado con tablas venezolanas (plan vial, Tarea 20).

- Acceso `LEER_PROYECTO` (arma y revisa, o clave de API), como `/v1/buscar/partidas`; el
  administrador recibe 403.
- `Cache-Control: no-store` en toda respuesta, también en 401, 403, 404, 422 y 503.
- Tabla desconocida: 404 con un mensaje fijo que no repite lo pedido; `q` de más de 80 caracteres o
  un `limite` fuera de 1..50: 422 fijo; un fallo de la base: 503 sin SQL ni rutas.
- Pide una sugerencia de más para saber si `hay_mas`, y la recorta.
- AC1b (Componer): `detalle` agrega la descripción y la unidad de cada insumo; `para_armar_al`
  agrega el precio de la lista para armar a esa fecha con su moneda y su fecha, o el aviso si está
  en otra moneda que la de la carpeta (`aplicacion.consulta`). Los campos que no vienen no se
  escriben (`response_model_exclude_none`): sin esos parámetros la respuesta es la de siempre. El
  precio viaja como texto decimal con punto. Una fecha mal escrita es el 422 fijo.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from api.acceso import LEER
from api.dependencias import SesionDep
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion.busqueda import LARGO_MAXIMO
from aplicacion.consulta import TABLAS, buscar

LIMITE_POR_OMISION = 10
LIMITE_MAXIMO = 50
MENSAJE_FORMA = (
    "La consulta no es válida: el texto admite hasta 80 caracteres y el límite va de 1 a 50."
)
MENSAJE_TABLA = "No hay una tabla de consulta con ese nombre."
MENSAJE_BASE = "No se pudo leer la tabla de consulta de la carpeta de trabajo."


class _RutaConsulta(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño de la Hoja §1.3-7)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/consulta", tags=["consulta"], route_class=_RutaConsulta)


class SugerenciaDeConsultaRespuesta(BaseModel):
    valor: str = Field(description="Lo que se guarda al elegir")
    etiqueta: str = Field(description="Lo que se lee en la lista")
    fuente: str = Field(description="De dónde sale el dato")
    descripcion: str | None = Field(None, description="Con `detalle`: la descripción del insumo")
    unidad: str | None = Field(None, description="Con `detalle`: la unidad del insumo, si la tiene")
    precio: str | None = Field(
        None,
        description=(
            "Con `para_armar_al`: el precio en la lista para armar a esa fecha, decimal con punto; "
            "nunca en otra moneda que la de la carpeta"
        ),
    )
    moneda: str | None = Field(None, description="La moneda de la lista de la que sale el precio")
    fecha_precio: date | None = Field(None, description="Desde cuándo rige esa lista")
    aviso_precio: str | None = Field(
        None, description="Si esa lista está en otra moneda: por qué no viene el precio"
    )


class ConsultaRespuesta(BaseModel):
    tabla: str
    resultados: list[SugerenciaDeConsultaRespuesta]
    hay_mas: bool = Field(description="Quedaron coincidencias fuera de `limite`")


@router.get(
    "/{tabla}",
    response_model=ConsultaRespuesta,
    response_model_exclude_none=True,
    dependencies=LEER,
)
def consultar(
    tabla: str,
    sesion: SesionDep,
    q: Annotated[str, Query(max_length=LARGO_MAXIMO, description="Código o palabras")] = "",
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO)] = LIMITE_POR_OMISION,
    detalle: Annotated[
        bool, Query(description="Insumos y salarios: agrega la descripción y la unidad")
    ] = False,
    para_armar_al: Annotated[
        date | None,
        Query(
            description=(
                "Insumos y salarios: agrega el precio de la lista para armar a esa fecha (ISO), "
                "con su moneda y su fecha, o el aviso si está en otra moneda"
            )
        ),
    ] = None,
) -> ConsultaRespuesta:
    """Sugerencias de una tabla (partidas_viales, insumos, tasa_bcv o salarios_cct), por
    relevancia, sin distinguir mayúsculas ni acentos. Con menos de 2 letras responde vacío (no
    es un error); una tabla desconocida es 404."""
    if tabla not in TABLAS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, MENSAJE_TABLA)
    try:
        halladas = buscar(
            sesion, tabla, q, limite=limite + 1, detalle=detalle, para_armar_al=para_armar_al
        )
    except SQLAlchemyError:
        # El texto de un error de base lleva el SQL y sus parámetros: no sale por la API.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None
    return ConsultaRespuesta(
        tabla=tabla,
        resultados=[
            SugerenciaDeConsultaRespuesta(
                valor=s.valor,
                etiqueta=s.etiqueta,
                fuente=s.fuente,
                descripcion=s.descripcion,
                unidad=s.unidad,
                precio=None if s.precio is None else str(s.precio),
                moneda=s.moneda,
                fecha_precio=s.fecha_precio,
                aviso_precio=s.aviso_precio,
            )
            for s in halladas[:limite]
        ],
        hay_mas=len(halladas) > limite,
    )
