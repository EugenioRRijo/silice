"""Rutas de rendimientos auditables y ejecuciones (UC-06, Sesion I6.2).

RF-25 (registro con trazabilidad a la ejecucion), RF-26 (historico con dispersion y propuesta) y
RF-27 (advertencia cuando el valor se aparta del comportamiento observado, **sin impedir** el
registro: la respuesta es 201 con el campo `advertencia`). La advertencia normativa es la del
rango observado (`core.catalog.advertencia_rendimiento`); si el extra `ml` esta instalado y el
historico alcanza, se enriquece con el veredicto del detector de anomalias de la Sesion I6.1
(`ml.anomaly.evaluar_rendimiento`) -- import perezoso, mismo criterio que el adaptador IFC en
`computos.py`: sin el extra, la ruta funciona igual con la advertencia de rango sola.
"""

from __future__ import annotations

import importlib.util
from decimal import Decimal

from fastapi import APIRouter, status
from sqlalchemy import select

from api.dependencias import SesionDep
from api.esquemas import (
    DispersionRespuesta,
    EjecucionPeticion,
    EjecucionRespuesta,
    PropuestaRendimientoRespuesta,
    RegistroRendimientoRespuesta,
    RendimientoPeticion,
    RendimientoRespuesta,
    RendimientosRespuesta,
    decimal_desde_texto,
)
from core import models
from core.catalog import (
    Catalogo,
    DispersionRendimiento,
    PropuestaRendimiento,
    advertencia_rendimiento,
    dispersion_rendimientos,
    justificar_rendimiento,
    proponer_rendimiento,
    registrar_ejecucion,
    registrar_rendimiento,
)
from core.contracts.apu import Rendimiento, TipoRendimiento

router = APIRouter(tags=["rendimientos"])


@router.post("/ejecuciones", response_model=EjecucionRespuesta, status_code=status.HTTP_201_CREATED)
def crear_ejecucion(sesion: SesionDep, peticion: EjecucionPeticion) -> EjecucionRespuesta:
    """Registra una obra ejecutada (referencia unica) y confirma la transaccion."""
    ejecucion = registrar_ejecucion(
        sesion,
        referencia=peticion.referencia,
        fecha_inicio=peticion.fecha_inicio,
        fecha_fin=peticion.fecha_fin,
        descripcion=peticion.descripcion,
    )
    sesion.commit()
    return EjecucionRespuesta.model_validate(ejecucion)


@router.get("/ejecuciones", response_model=list[EjecucionRespuesta])
def listar_ejecuciones(sesion: SesionDep) -> list[EjecucionRespuesta]:
    """Obras ejecutadas registradas, de la mas antigua a la mas reciente."""
    consulta = select(models.Ejecucion).order_by(models.Ejecucion.fecha_inicio, models.Ejecucion.id)
    return [EjecucionRespuesta.model_validate(e) for e in sesion.scalars(consulta)]


@router.get("/partidas/{codigo}/rendimientos", response_model=RendimientosRespuesta)
def obtener_rendimientos(sesion: SesionDep, codigo: str) -> RendimientosRespuesta:
    """El historico de la partida con su dispersion y su propuesta (RF-26)."""
    historico = Catalogo(sesion).rendimientos(codigo)  # KeyError -> 404 si la partida no existe
    dispersion = dispersion_rendimientos(sesion, codigo)
    return RendimientosRespuesta(
        historico=[_a_rendimiento_respuesta(r) for r in historico],
        dispersion=_a_dispersion_respuesta(dispersion) if dispersion is not None else None,
        propuesta=propuesta_respuesta(proponer_rendimiento(sesion, codigo)),
    )


@router.post(
    "/partidas/{codigo}/rendimientos",
    response_model=RegistroRendimientoRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_rendimiento(
    sesion: SesionDep, codigo: str, peticion: RendimientoPeticion
) -> RegistroRendimientoRespuesta:
    """RF-25 + RF-27: registra el rendimiento y advierte si se aparta de lo observado.

    La advertencia se evalua contra el comportamiento observado ANTES de este registro (el valor
    nuevo no participa de su propio rango) y nunca impide: con un valor valido la respuesta es 201
    con el registro hecho y la transaccion confirmada, haya advertencia o no. La unica excepcion
    que trae UC-06 4a es una justificacion en blanco junto a una advertencia (422, ver abajo).

    UC-06, flujo 4a (INV-093): si hubo advertencia y la peticion trae `justificacion`, se registra
    con `justificar_rendimiento`, que la liga al ultimo rendimiento de la partida, el que esta
    misma peticion acaba de registrar en su transaccion (revision de arquitectura de C6, N-5). Sin
    advertencia la justificacion se ignora: el cliente no sabe de antemano si la habra, y
    rechazarla impediria un registro que RF-27 no impide. Si el nucleo la rechaza (en blanco), se
    deshace tambien el rendimiento y la respuesta es 422: la peticion es una sola operacion.
    """
    valor = decimal_desde_texto(peticion.valor, "valor")
    try:
        tipo = TipoRendimiento(peticion.tipo)
    except ValueError:
        raise ValueError(
            f"tipo de rendimiento desconocido: {peticion.tipo!r} (use 'estimado' o 'medido')"
        ) from None

    historico_previo = Catalogo(sesion).rendimientos(codigo)  # KeyError -> 404
    dispersion_previa = dispersion_rendimientos(sesion, codigo)

    registrado = registrar_rendimiento(
        sesion,
        codigo,
        valor=valor,
        tipo=tipo,
        fecha=peticion.fecha,
        condiciones=peticion.condiciones,
        referencia_ejecucion=peticion.referencia_ejecucion,
    )
    advertencia = _advertencia(dispersion_previa, historico_previo, valor)
    justificacion = None
    if advertencia is not None and peticion.justificacion is not None:
        try:
            justificacion = justificar_rendimiento(
                sesion, codigo, peticion.justificacion, advertencia, peticion.fecha
            ).texto
        except ValueError:
            sesion.rollback()
            raise
    sesion.commit()

    return RegistroRendimientoRespuesta(
        rendimiento=_a_rendimiento_respuesta(registrado),
        advertencia=advertencia,
        justificacion=justificacion,
    )


# ---------------------------------------------------------------------------------------------
# Ayudantes
# ---------------------------------------------------------------------------------------------


def propuesta_respuesta(
    propuesta: PropuestaRendimiento | None,
) -> PropuestaRendimientoRespuesta | None:
    """La propuesta de `proponer_rendimiento` como respuesta (RF-26); la usan esta ruta y el 409
    de `POST /presupuestos` (UC-01, flujo 3b)."""
    if propuesta is None:
        return None
    return PropuestaRendimientoRespuesta(
        rendimiento=_a_rendimiento_respuesta(propuesta.rendimiento),
        dispersion=_a_dispersion_respuesta(propuesta.dispersion),
    )


def _advertencia(
    dispersion_previa: DispersionRendimiento | None,
    historico_previo: list[Rendimiento],
    valor: Decimal,
) -> str | None:
    """La advertencia de rango (normativa, RF-27) mas el veredicto del bosque si esta disponible."""
    partes = []
    por_rango = advertencia_rendimiento(dispersion_previa, valor)
    if por_rango is not None:
        partes.append(por_rango)

    veredicto = _veredicto_bosque([r.valor for r in historico_previo], valor)
    if veredicto is not None and veredicto.atipico:
        partes.append(
            "el detector de anomalias (Isolation Forest, Sesion I6.1) tambien lo marca "
            f"atipico (puntaje {veredicto.puntaje:.3f})"
        )
    return "; ".join(partes) or None


def _veredicto_bosque(valores_previos: list[Decimal], valor: Decimal):
    """El veredicto de `ml.anomaly`, o `None` sin el extra `ml` o sin historico suficiente.

    El extra se reconoce por `scikit-learn` (`importlib.util.find_spec`), no por `ml.anomaly`, que
    se importa solo con `numpy`: el bosque importa `sklearn` al evaluar (ronda 1 de la pista A,
    H3; el mismo criterio que `presupuestos._detector_de_atipicos`).
    """
    if importlib.util.find_spec("sklearn") is None:
        return None
    try:
        from ml.anomaly import evaluar_rendimiento
    except ImportError:
        return None
    return evaluar_rendimiento(valores_previos, valor)


def _a_rendimiento_respuesta(rendimiento: Rendimiento) -> RendimientoRespuesta:
    return RendimientoRespuesta(
        valor=str(rendimiento.valor),
        tipo=rendimiento.tipo.value,
        fecha=rendimiento.fecha,
        condiciones=rendimiento.condiciones,
        referencia_ejecucion=rendimiento.referencia_ejecucion,
    )


def _a_dispersion_respuesta(dispersion: DispersionRendimiento) -> DispersionRespuesta:
    return DispersionRespuesta(
        observaciones=dispersion.observaciones,
        media=str(dispersion.media),
        minimo=str(dispersion.minimo),
        maximo=str(dispersion.maximo),
        medidos=dispersion.medidos,
        estimados=dispersion.estimados,
    )
