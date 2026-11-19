"""Rutas de escenarios y comparativos de un presupuesto (UC-08 y RF-31).

`POST /presupuestos/{codigo}/escenarios` recalcula el base bajo cada supuesto sin guardar nada,
`GET .../escenarios/base` precarga el formulario con los parametros congelados del base y
`POST .../escenarios/csv` devuelve la tabla de RF-31 para Excel en español (dos decimales).
Salieron de `api/rutas/presupuestos.py` sin cambios (tarea 4.1 del plan de desenredo); `api/main.py`
registra este router despues del de presupuestos y del de calculo, asi el orden de las rutas
no cambia.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from api.acceso import EDITAR, LEER
from api.dependencias import SesionDep
from api.esquemas import (
    EscenarioRespuesta,
    EscenariosPeticion,
    EscenariosRespuesta,
    PendienteRespuesta,
)
from api.esquemas_ola2 import EscenariosBaseRespuesta
from api.rutas.presupuestos_ayudas import (
    _CAMPOS_PARAMETROS,
    _buscar_modelo,
    _campos_pendiente,
    _filas_comparativo,
    _generar_escenarios,
    _neutralizar_formula,
)
from aplicacion import elaboracion as aplicacion_elaboracion
from aplicacion.escenarios_csv import csv_de_escenarios
from core.budget import (
    cargar_elaboracion,
    comparar_escenarios,
    comparar_por_partida,
)
from core.catalog import Catalogo
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

router = APIRouter(tags=["presupuestos"])


@router.post(
    "/presupuestos/{codigo}/escenarios", response_model=EscenariosRespuesta, dependencies=EDITAR
)
def escenarios_de_presupuesto(
    sesion: SesionDep,
    codigo: str,
    peticion: EscenariosPeticion,
    proyecto: str | None = None,
) -> EscenariosRespuesta:
    """UC-08: recalcula el presupuesto bajo los supuestos de cada escenario, sin persistir nada.

    Los parámetros que un escenario no declara heredan los congelados en el presupuesto base;
    un parámetro fuera de rango lo rechaza el contrato (`ParametrosCosto`) y responde 422
    (flujo 1a). La sesión no confirma nada: el base queda como única versión guardada (RF-30).

    Los ítems pendientes del base (sin partida en el catálogo, UC-01 flujo 3a) no se recalculan en
    ningún escenario ni suman a ningún total: la respuesta los lista en `pendientes_base`, con la
    misma forma que los pendientes de `POST /presupuestos` pero sin propuestas. Los hallazgos de
    cada escenario no los cuentan.
    """
    _modelo, elaboracion, escenarios, sin_efecto = _generar_escenarios(
        sesion, codigo, proyecto, peticion
    )
    base = elaboracion.presupuesto
    comparativos = [comparar_por_partida(base, escenario) for escenario in escenarios]

    respuestas: list[EscenarioRespuesta] = []
    for escenario, comparativo, sin in zip(escenarios, comparativos, sin_efecto, strict=True):
        respuestas.append(
            EscenarioRespuesta(
                nombre=escenario.nombre,
                total=formatear_decimal(escenario.presupuesto.total, DECIMALES_PRESENTACION),
                variacion=formatear_decimal(comparativo.variacion, DECIMALES_PRESENTACION),
                variacion_pct=formatear_decimal(comparativo.variacion_pct, DECIMALES_PRESENTACION),
                hallazgos=len(escenario.informe.hallazgos),
                insumos_variados=escenario.insumos_variados,
                precios_sin_insumo=list(sin.sin_insumo),
                precios_sin_cambio=list(sin.sin_cambio),
                partidas=_filas_comparativo(comparativo),
            )
        )
    return EscenariosRespuesta(
        codigo_base=base.codigo,
        total_base=formatear_decimal(base.total, DECIMALES_PRESENTACION),
        pendientes_base=[
            PendienteRespuesta(**_campos_pendiente(item)) for item in elaboracion.pendientes
        ],
        escenarios=respuestas,
    )


@router.get(
    "/presupuestos/{codigo}/escenarios/base",
    response_model=EscenariosBaseRespuesta,
    dependencies=LEER,
)
def base_de_escenarios(
    sesion: SesionDep, codigo: str, proyecto: str | None = None
) -> EscenariosBaseRespuesta:
    """El presupuesto base de la página de escenarios (UC-08): sus parámetros de costo congelados,
    exactos, para precargar el formulario, y los ítems pendientes que ningún escenario recalcula
    (INV-083)."""
    modelo = _buscar_modelo(sesion, codigo, proyecto)
    elaboracion = cargar_elaboracion(sesion, modelo.proyecto.nombre, codigo, Catalogo(sesion))
    base = elaboracion.presupuesto
    return EscenariosBaseRespuesta(
        codigo=base.codigo,
        proyecto=modelo.proyecto.nombre,
        moneda=base.moneda,
        total=formatear_decimal(base.total, DECIMALES_PRESENTACION),
        parametros={nombre: str(getattr(modelo, nombre)) for nombre in _CAMPOS_PARAMETROS},
        pendientes_base=[
            PendienteRespuesta(**_campos_pendiente(item)) for item in elaboracion.pendientes
        ],
    )


@router.post("/presupuestos/{codigo}/escenarios/csv", dependencies=EDITAR, response_class=Response)
def escenarios_en_csv(
    sesion: SesionDep,
    codigo: str,
    peticion: EscenariosPeticion,
    proyecto: str | None = None,
) -> Response:
    """La tabla de RF-31 (el base y una fila por escenario) como CSV para Excel en español: `;`,
    coma decimal, punto de miles y los dos decimales de la pantalla (`aplicacion/escenarios_csv.py`;
    prueba en vivo del 2026-11-18). Mismo cuerpo y mismos errores que
    `POST /presupuestos/{codigo}/escenarios`; no guarda nada."""
    _modelo, elaboracion, escenarios, _sin_efecto = _generar_escenarios(
        sesion, codigo, proyecto, peticion
    )
    tabla = comparar_escenarios(elaboracion.presupuesto, escenarios)
    # El nombre de un escenario y el codigo del base son texto de la persona: Excel evaluaria como
    # formula uno que empiece por = + - @ (mismo criterio que el libro, core/budget/excel.py).
    tabla["escenario"] = [_neutralizar_formula(texto) for texto in tabla["escenario"]]
    nombre = aplicacion_elaboracion.nombre_de_archivo("escenarios", codigo, "csv")
    return Response(
        content=csv_de_escenarios(tabla.to_dict("records")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
