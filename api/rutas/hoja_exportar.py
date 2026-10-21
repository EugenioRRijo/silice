"""`/v1/hoja/borradores/{id}/excel`: exportar el borrador vivo a Excel (T10, 3e-1, ruta X1).

Es el boton «Descargar Excel» de la pagina clasica (`ui/paginas/hoja.py:556-573`) hecho servicio
sobre `aplicacion.hoja_exportar`. `GET` sin cuerpo ni `rev`: arma el libro del borrador vivo (con
la trazabilidad, los precios y las hojas de control si hay una version abierta) y lo devuelve como
adjunto. **No escribe nada** (ni la base ni el borrador ni su `rev`).

Acceso, borrador ajeno (404), otro caso (409) y `no-store` son los de las demas rutas del borrador
(`api.rutas.hoja`): solo una cuenta con `EDITAR_HOJA`; con `X-Silice-Clave`, 403. El router lleva
`RutaSinCache` y `RutaSinEco` EN ESE ORDEN (al reves, la primera atrapa el 422 de forma antes y lo
devuelve con eco).

Errores propios: 422 `No se pudo preparar el Excel: {error}` si el libro lanza `ValueError`
(paridad con P:571) y 503 fijo si falla la base (no se repite el `orig` del driver).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import SesionDep
from api.rutas import hoja as rutas_hoja
from api.rutas.hoja import CuentaDeLaHoja, IdDeBorrador
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion import hoja_exportar

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class _RutaExportar(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseno §1.3-7)."""

    mensaje_por_omision = rutas_hoja.MENSAJE_FORMA


router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaExportar)


@router.get(
    "/borradores/{id}/excel",
    response_class=Response,
    responses={200: {"content": {TIPO_XLSX: {}}, "description": "El libro .xlsx del borrador."}},
)
def exportar_excel(
    id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja, sesion: SesionDep
) -> Response:
    """X1: el libro del borrador vivo. En la firma `activa` va antes que `sesion`: el acceso (401,
    403) debe responder antes de abrir la base del caso."""
    vivo = rutas_hoja._vivo(request, activa, id)
    try:
        nombre, contenido = hoja_exportar.excel_del_borrador(vivo, sesion, rutas_hoja._hoy())
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail=f"No se pudo preparar el Excel: {error}"
        ) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=rutas_hoja.MENSAJE_BASE) from None
    return Response(
        content=contenido,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
