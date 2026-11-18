"""`/v1/hoja` S2 a S6 (3d-2): versiones nuevas desde una guardada y la cadena de sellos.

- S2 `POST /versiones/restaurar`, S3 `POST /versiones/cotizar`, S4
  `POST /versiones/retirar-cotizacion` y S5 `POST /versiones/convertir`: cada una crea una
  version nueva y vigente a nombre de la persona de la sesion.
- S6 `GET /cadena`: el estado de integridad de la cadena de sellos del proyecto; solo lee.

Salieron de `api/rutas/hoja.py` sin cambios (tarea 4.2 del plan de desenredo), con su misma
clase de ruta (`_RutaHoja`); el «hoy» de S5 es `rutas_hoja._hoy()`, el de toda la Hoja.
`api/main.py` registra este router despues del de la hoja y del de sus lecturas, asi el orden
de las rutas no cambia.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import SesionDeEscrituraDep, SesionDep
from api.esquemas_hoja import (
    CadenaHojaRespuesta,
    ConvertirVersion,
    CotizarVersion,
    RestaurarVersion,
    RetirarCotizacion,
    VersionNuevaRespuesta,
    cadena_a_respuesta,
    version_nueva_a_respuesta,
)
from api.rutas import hoja as rutas_hoja
from api.rutas.hoja import (
    FORMA_CADENA,
    FORMA_CONVERTIR,
    FORMA_COTIZAR,
    FORMA_RESTAURAR,
    FORMA_RETIRAR,
    MENSAJE_BASE,
    VER,
    CuentaDeLaHoja,
    CuentaQueConvierte,
    _RutaHoja,
)
from api.sin_eco import sin_eco
from aplicacion import hoja_versiones
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_versiones import ProyectoInexistente, VersionInexistente, VersionNueva
from core.catalog import CatalogoIncompleto

router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaHoja)


def _crear_version(operacion: Callable[[], VersionNueva]) -> VersionNuevaRespuesta:
    """Corre una operacion que crea una version y traduce sus errores: 404 (el proyecto o la
    version no existen), 422 (un dato de dominio, con el texto de la clasica), 409
    (`CatalogoIncompleto`: falta una composicion) y 503 (la base). Lo inesperado sube: tras
    deshacer, FastAPI responde su 500 generico sin detalle."""
    try:
        return version_nueva_a_respuesta(operacion())
    except (ProyectoInexistente, VersionInexistente) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except HojaInvalida as error:  # antes que ValueError: es una subclase
        raise HTTPException(status_code=422, detail=str(error)) from None
    except (ValueError, CatalogoIncompleto) as error:
        raise HTTPException(status_code=409, detail=f"No se guardó nada: {error}") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


@router.post("/versiones/restaurar", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_RESTAURAR)
def restaurar_version(
    datos: RestaurarVersion, activa: CuentaDeLaHoja, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S2: restaura una versión anterior como versión nueva y vigente (RF-54). Escribe en una
    transacción con `BEGIN IMMEDIATE` y la cadena de sellos cubriendo los anexos; el responsable
    es la persona de la sesión. `activa` va antes que `sesion`: el acceso responde antes de abrir
    la base del caso."""
    return _crear_version(
        lambda: hoja_versiones.restaurar(
            sesion,
            datos.proyecto,
            datos.version,
            fuente=datos.fuente,
            responsable=activa.usuario,
        )
    )


@router.post("/versiones/cotizar", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_COTIZAR)
def cotizar_insumo(
    datos: CotizarVersion, activa: CuentaDeLaHoja, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S3: cotiza un insumo para el proyecto y guarda la versión nueva (RF-56). El precio llega
    como texto; solo cambia ese insumo en ese proyecto."""
    return _crear_version(
        lambda: hoja_versiones.cotizar(
            sesion,
            datos.proyecto,
            datos.version,
            insumo=datos.insumo,
            precio=datos.precio,
            proveedor=datos.proveedor,
            numero=datos.numero,
            fecha=datos.fecha,
            evidencia=datos.evidencia,
            responsable=activa.usuario,
        )
    )


@router.post("/versiones/retirar-cotizacion", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_RETIRAR)
def retirar_cotizacion(
    datos: RetirarCotizacion, activa: CuentaDeLaHoja, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S4: retira la cotización de un insumo; la versión nueva vuelve al precio de la lista base."""
    return _crear_version(
        lambda: hoja_versiones.retirar_cotizacion(
            sesion,
            datos.proyecto,
            datos.version,
            insumo=datos.insumo,
            motivo=datos.motivo,
            responsable=activa.usuario,
        )
    )


@router.post("/versiones/convertir", response_model=VersionNuevaRespuesta)
@sin_eco(FORMA_CONVERTIR)
def convertir_version(
    datos: ConvertirVersion, activa: CuentaQueConvierte, sesion: SesionDeEscrituraDep
) -> VersionNuevaRespuesta:
    """S5: convierte la versión a otra moneda con la tasa del BCV de hoy (RF-64). Exige
    `CONVERTIR_Y_REAJUSTAR` (la matriz de permisos), no solo editar la hoja."""
    return _crear_version(
        lambda: hoja_versiones.convertir(
            sesion,
            datos.proyecto,
            datos.version,
            datos.moneda,
            lado=datos.lado,
            fecha=rutas_hoja._hoy(),
            fuente=datos.fuente,
            responsable=activa.usuario,
        )
    )


@router.get("/cadena", response_model=CadenaHojaRespuesta, dependencies=[VER])
@sin_eco(FORMA_CADENA)
def cadena_de_sellos(
    sesion: SesionDep, proyecto: Annotated[str, Query(min_length=1, max_length=500)]
) -> CadenaHojaRespuesta:
    """S6: el estado de integridad de la cadena de sellos del proyecto (recalcula cada huella).
    Clave de API o sesión con `LEER_PROYECTO`; solo lee."""
    try:
        return cadena_a_respuesta(hoja_versiones.estado_de_la_cadena(sesion, proyecto))
    except ProyectoInexistente as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
