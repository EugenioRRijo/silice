"""Rutas del calculo de ensayo de un presupuesto (UC-01 en modo «solo calcular»).

`POST /presupuestos/calcular` elabora y audita sin guardar nada, `POST .../calcular/excel` da el
libro del mismo calculo y `POST .../calcular/declarar-rendimiento` registra el rendimiento que
propone el historico (flujo 3b). Salieron de `api/rutas/presupuestos.py` sin cambios (tarea 4.1
del plan de desenredo); `api/main.py` registra este router justo despues del de presupuestos y
antes del de escenarios, asi el orden de las rutas no cambia.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, Response

from api.acceso import EDITAR
from api.dependencias import SesionDeEscrituraDep, SesionDep
from api.esquemas import RendimientosPorDeclararRespuesta
from api.esquemas_informe import informe_a_respuesta
from api.esquemas_ola2 import (
    CalculoPeticion,
    CalculoRespuesta,
    DeclararRendimientoPeticion,
    DeclararRendimientoRespuesta,
    FilaPlan,
)
from api.rutas.presupuestos_ayudas import (
    _QUIEN_EDITA,
    _elaborar_sin_guardar,
    _partidas_respuesta,
    _pendientes_con_propuestas,
)
from aplicacion import elaboracion as aplicacion_elaboracion
from core.contracts.apu import TipoRendimiento
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from seguridad.sesiones import SesionActiva

router = APIRouter(tags=["presupuestos"])


@router.post(
    "/presupuestos/calcular",
    response_model=CalculoRespuesta,
    dependencies=[Depends(_QUIEN_EDITA)],  # antes que la sesión: sin permiso no se abre el caso
    responses={
        status.HTTP_409_CONFLICT: {
            "model": RendimientosPorDeclararRespuesta,
            "description": "Falta un dato vigente del catálogo; si es un rendimiento estimado, "
            "la respuesta propone el del histórico (UC-01, flujo 3b)",
        }
    },
)
def calcular_presupuesto(
    sesion: SesionDep,
    peticion: CalculoPeticion,
    quien: Annotated[SesionActiva | None, Depends(_QUIEN_EDITA)],
) -> CalculoRespuesta | JSONResponse:
    """UC-01 en modo «solo calcular» (la página Elaborar de Streamlit): elabora y audita el
    presupuesto con las composiciones del catálogo a la fecha, sin guardar nada.

    El informe de auditoría viaja como JSON (siempre, UC-05). Los ítems sin partida quedan
    pendientes con sus partidas similares (flujo 3a); aceptar una propuesta es volver a enviar el
    ítem con ese código. `plan` son las filas de la tabla del plan de trabajo (paso 6); sin ellas,
    `plan_secuencial`. Una partida sin rendimiento estimado vigente responde 409 con el que
    propone el histórico (flujo 3b), que se declara con `POST /presupuestos/calcular/declarar-
    rendimiento`. Con `proyecto` valora con la lista de esa obra (`lista_para_el_proyecto`) y en su
    moneda: así Elaborar muestra lo que la Hoja valorará al llevarle los ítems (Tarea 12). Sigue
    sin guardar nada: la lista convertida de una obra en la otra moneda se deshace al terminar.
    Una obra que no existe, 404; sin lista para armar o sin tasa del BCV, 409 con su texto.
    """
    calculo = _elaborar_sin_guardar(sesion, peticion, quien)
    if isinstance(calculo, JSONResponse):
        return calculo
    resultado, descripciones = calculo
    presupuesto = resultado.presupuesto
    return CalculoRespuesta(
        codigo=presupuesto.codigo,
        fecha=presupuesto.fecha,
        moneda=presupuesto.moneda,
        total=formatear_decimal(presupuesto.total, DECIMALES_PRESENTACION),
        total_exacto=f"{presupuesto.total:f}",
        partidas=_partidas_respuesta(presupuesto),
        por_severidad=informe_a_respuesta(resultado.informe).por_severidad,
        informe=informe_a_respuesta(resultado.informe),
        pendientes=_pendientes_con_propuestas(descripciones, resultado.pendientes),
        plan_por_defecto=[
            FilaPlan(**fila)
            for fila in aplicacion_elaboracion.filas_del_plan_por_defecto(presupuesto)
        ],
    )


@router.post(
    "/presupuestos/calcular/excel",
    dependencies=[Depends(_QUIEN_EDITA)],
    response_class=Response,
)
def calcular_presupuesto_excel(
    sesion: SesionDep,
    peticion: CalculoPeticion,
    quien: Annotated[SesionActiva | None, Depends(_QUIEN_EDITA)],
) -> Response:
    """El libro de Excel (con su hoja de auditoría) del mismo cálculo de `POST
    /presupuestos/calcular`, que recalcula con el mismo cuerpo: sin estado, nada se guarda."""
    calculo = _elaborar_sin_guardar(sesion, peticion, quien)
    if isinstance(calculo, JSONResponse):
        return calculo
    libro, nombre = aplicacion_elaboracion.libro_excel(calculo[0])
    return Response(
        content=libro,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post(
    "/presupuestos/calcular/declarar-rendimiento",
    response_model=DeclararRendimientoRespuesta,
    dependencies=EDITAR,
)
def declarar_rendimiento_propuesto(
    sesion: SesionDeEscrituraDep, peticion: DeclararRendimientoPeticion
) -> DeclararRendimientoRespuesta:
    """UC-01, flujo 3b: registra el rendimiento que propone el histórico para una partida sin
    rendimiento estimado vigente a `fecha`, con el tipo que declara el proyectista.

    Solo un rendimiento declarado **estimado** desbloquea la elaboración: declarado medido es 422 y
    no se registra nada. Una partida que ya tiene uno vigente es 422; una que no existe, 404.
    """
    por_declarar = aplicacion_elaboracion.rendimiento_por_declarar(
        sesion, peticion.codigo_partida, peticion.fecha
    )
    rendimiento = aplicacion_elaboracion.declarar_rendimiento(
        sesion, por_declarar, TipoRendimiento(peticion.tipo), peticion.fecha
    )
    sesion.commit()
    return DeclararRendimientoRespuesta(
        codigo_partida=rendimiento.codigo_partida,
        valor=str(rendimiento.valor),
        tipo=rendimiento.tipo.value,
        fecha=rendimiento.fecha,
        condiciones=rendimiento.condiciones,
    )
