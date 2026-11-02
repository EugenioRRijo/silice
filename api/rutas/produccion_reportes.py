"""`/v1/produccion/reportes`: el reporte de costo de producción en Excel (plan vial, Tarea 21).

Vivía en `/v1/vial/reportes/produccion` con `editar_hoja` y el módulo vial, así que solo lo bajaba
`arma` y no el administrador que publica el costo (fila 112 de las preguntas para Eugenio y MENOR 1
del árbitro de la fase D). Aquí lleva su propia puerta:

- `GET /produccion?periodo=AAAA-MM` → un libro .xlsx (`aplicacion.reportes_viales.
  costo_de_produccion_del_periodo`) con la portada que dice de dónde sale cada cifra, los cálculos
  del período, su costo por tonelada, los costos y lo producido. Solo lee la instalación (no la
  carpeta del caso: el administrador lo baja sin abrir una). Sin `periodo`: 422 con un mensaje fijo;
  período mal escrito: 422 del dominio; sin cálculos en el período: 404 que nombra el período; la
  base, 503.

Acceso: `REGISTRAR_COSTOS` (`Accion.REGISTRAR_COSTOS_PRODUCCION`, arma y administrador; clave de API
o sesión) y **después** el módulo producción (`requiere_modulo`, D-V-4): sin sesión 401, sin el rol
403, con el rol y el módulo apagado 404. `Cache-Control: no-store`. Un router aparte para no sumar
la puerta de la arenera (`OPERAR_ARENERA`) que no es la de los costos, y para no estirar
`produccion_planta`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import SQLAlchemyError

from api.acceso_modulos import requiere_modulo
from api.dependencias import SesionInstalacionDep
from api.rutas.hoja_exportar import TIPO_XLSX
from api.rutas.produccion_planta import REGISTRAR_COSTOS
from api.sin_cache import RutaSinCache
from aplicacion import reportes_viales

MENSAJE_PERIODO = "Envíe el período del reporte como AAAA-MM (periodo)."
MENSAJE_BASE = (
    "No se pudo leer la instalación. Revise que el archivo exista y no esté abierto en otro "
    "programa."
)

router = APIRouter(
    prefix="/v1/produccion/reportes",
    tags=["produccion"],
    # El orden importa: primero quién es y si registra costos; luego si el módulo está encendido.
    dependencies=[Depends(REGISTRAR_COSTOS), Depends(requiere_modulo("produccion"))],
    route_class=RutaSinCache,
)

__all__ = ["MENSAJE_PERIODO", "router"]


@router.get(
    "/produccion",
    response_class=Response,
    responses={200: {"content": {TIPO_XLSX: {}}, "description": "El libro .xlsx del reporte."}},
)
def reporte_de_produccion(
    instalacion: SesionInstalacionDep,
    periodo: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
) -> Response:
    """El costo de producción de un período en Excel; solo lee."""
    if periodo is None:
        raise HTTPException(status_code=422, detail=MENSAJE_PERIODO)
    try:
        contenido = reportes_viales.costo_de_produccion_del_periodo(instalacion, periodo)
    except reportes_viales.SinCalculosDelPeriodo as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    nombre = reportes_viales.nombre_de_reporte("produccion", periodo)
    return Response(
        content=contenido,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
