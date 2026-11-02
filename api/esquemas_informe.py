"""El informe de auditoría (UC-05) como JSON, para la interfaz nueva (ola 2 de la sesión 2b).

`GET /presupuestos/{codigo}/informe` sigue siendo Markdown (integraciones). La interfaz nueva
recibe esta estructura y dibuja cada celda como texto plano (SEG-3): la descripción de un hallazgo
puede traer el nombre de un insumo importado, que en Markdown sería un enlace o una imagen. Los
montos viajan con los dos decimales del sistema (`DECIMALES_PRESENTACION`), como `ui/resultado.py`.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from core.verification.informe import DECIMALES_PRESENTACION, SIN_HALLAZGOS, InformeAuditoria
from core.verification.texto import formatear_decimal


class HallazgoRespuesta(BaseModel):
    numero: int
    regla: str
    severidad: str
    partida: str | None
    descripcion: str
    impacto: str | None
    observado: str | None
    esperado: str | None
    origen: list[str]


class ReglaEvaluadaRespuesta(BaseModel):
    regla: str
    nombre: str
    hallazgos: int


class SeveridadRespuesta(BaseModel):
    severidad: str
    total: int


class InformeAuditoriaRespuesta(BaseModel):
    codigo_presupuesto: str
    cumple: bool
    veredicto: str
    total_hallazgos: int
    por_severidad: list[SeveridadRespuesta]
    reglas_evaluadas: list[ReglaEvaluadaRespuesta]
    hallazgos: list[HallazgoRespuesta]
    #: El texto que declara que se verificó y no hubo nada (UC-05 5a); `None` si hay hallazgos.
    sin_hallazgos: str | None


def _monto(valor: Decimal | None) -> str | None:
    return None if valor is None else formatear_decimal(valor, DECIMALES_PRESENTACION)


def informe_a_respuesta(informe: InformeAuditoria) -> InformeAuditoriaRespuesta:
    return InformeAuditoriaRespuesta(
        codigo_presupuesto=informe.codigo_presupuesto,
        cumple=informe.cumple,
        veredicto="CUMPLE" if informe.cumple else "NO CUMPLE",
        total_hallazgos=len(informe.hallazgos),
        por_severidad=[
            SeveridadRespuesta(severidad=severidad.name, total=total)
            for severidad, total in informe.por_severidad().items()
        ],
        reglas_evaluadas=[
            ReglaEvaluadaRespuesta(regla=codigo, nombre=nombre, hallazgos=cuenta)
            for codigo, nombre, cuenta in informe.cuenta_por_regla_evaluada()
        ],
        hallazgos=[
            HallazgoRespuesta(
                numero=numero,
                regla=h.regla,
                severidad=h.severidad.name,
                partida=informe.partida_de(h),
                descripcion=h.descripcion,
                impacto=_monto(h.impacto),
                observado=_monto(h.valor_observado),
                esperado=_monto(h.valor_esperado),
                origen=list(h.origen_ids),
            )
            for numero, h in enumerate(informe.hallazgos, start=1)
        ],
        sin_hallazgos=None if informe.hallazgos else SIN_HALLAZGOS,
    )
