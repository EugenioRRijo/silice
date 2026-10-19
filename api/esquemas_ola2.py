"""Esquemas de las rutas de la ola 2 de la migración (Actualizar precios, Elaborar, Escenarios).

Módulo aparte: `api/esquemas.py` no se toca (reparto de la sesión 2b). Los montos viajan como
texto, con los dos decimales del sistema salvo donde se dice «exacto».
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from api.esquemas import (
    FilaComparativoRespuesta,
    ItemComputoPeticion,
    PartidaPresupuestadaRespuesta,
    PendienteRespuesta,
    PresupuestoResumenRespuesta,
    PropuestaPartidaRespuesta,
)
from api.esquemas_informe import InformeAuditoriaRespuesta, SeveridadRespuesta

# ---------------------------------------------------------------------------------------------
# Listado con proyecto
# ---------------------------------------------------------------------------------------------


class PresupuestoConProyectoRespuesta(PresupuestoResumenRespuesta):
    """`PresupuestoResumenRespuesta` más el nombre del proyecto (el código solo es único por
    proyecto): lo que necesitan los selectores de la interfaz nueva."""

    proyecto: str


# ---------------------------------------------------------------------------------------------
# Actualizar precios (UC-02)
# ---------------------------------------------------------------------------------------------


class InsumoDesconocidoRespuesta(BaseModel):
    descripcion: str
    tipo: str
    unidad: str | None
    precio: str
    #: Cómo lo lee la persona: «descripción (tipo, unidad)».
    etiqueta: str


class VistaPreviaRespuesta(BaseModel):
    """Los insumos del archivo que se pueden dar de alta (flujo 2a), sin escribir nada. Un archivo
    que no se puede leer no ofrece nada y trae su motivo; el mismo fallo se informa al revalorar."""

    desconocidos: list[InsumoDesconocidoRespuesta]
    motivo: str | None = None


class AvisoRespuesta(BaseModel):
    nivel: Literal["info", "advertencia"]
    texto: str


class RevaloracionRespuesta(BaseModel):
    proyecto: str
    codigo_base: str
    codigo_nuevo: str
    moneda: str
    total_anterior: str
    total_nuevo: str
    variacion: str
    variacion_pct: str
    #: «anterior -> nuevo MONEDA  (variación MONEDA, porcentaje %)», como la página de Streamlit.
    resumen: str
    insumos_afectados: int
    filas: list[FilaComparativoRespuesta]
    dados_de_alta: list[str]
    ignorados: list[str]
    rechazados: list[str]
    #: El código de la versión que esta petición guardó; `null` si ningún precio cambió (3a).
    version_guardada: str | None
    avisos: list[AvisoRespuesta]
    informe: InformeAuditoriaRespuesta


class DescarteRespuesta(BaseModel):
    codigo: str
    descartada: bool
    fecha: date


# ---------------------------------------------------------------------------------------------
# Elaborar un presupuesto (UC-01), sin guardar
# ---------------------------------------------------------------------------------------------


class FilaPlan(BaseModel):
    """Una fila de la tabla del plan de trabajo; los textos pueden venir en blanco (fila nueva)."""

    periodo: str = ""
    codigo_partida: str = ""
    fraccion: str = ""


class CalculoPeticion(BaseModel):
    """UC-01 en modo «solo calcular»: nada se guarda. `plan` son las filas de la tabla del
    proyectista; sin ellas, el plan por defecto (`plan_secuencial`)."""

    codigo: str
    fecha: date
    moneda: str = "USD"
    items: list[ItemComputoPeticion]
    plan: list[FilaPlan] | None = None


class PendienteConPropuestasRespuesta(PendienteRespuesta):
    """Un ítem sin partida con las partidas similares que se le proponen (o por qué no hay)."""

    propuestas: list[PropuestaPartidaRespuesta]
    falla: str | None = None


class CalculoRespuesta(BaseModel):
    codigo: str
    fecha: date
    moneda: str
    total: str
    partidas: list[PartidaPresupuestadaRespuesta]
    por_severidad: list[SeveridadRespuesta]
    informe: InformeAuditoriaRespuesta
    pendientes: list[PendienteConPropuestasRespuesta]
    #: Las filas del plan por defecto, para precargar la tabla del plan de trabajo.
    plan_por_defecto: list[FilaPlan]


class DeclararRendimientoPeticion(BaseModel):
    codigo_partida: str
    tipo: Literal["estimado", "medido"]
    fecha: date


class DeclararRendimientoRespuesta(BaseModel):
    codigo_partida: str
    valor: str
    tipo: str
    fecha: date
    condiciones: str


# ---------------------------------------------------------------------------------------------
# Escenarios de sensibilidad (UC-08)
# ---------------------------------------------------------------------------------------------


class EscenariosBaseRespuesta(BaseModel):
    """El presupuesto base de la página de escenarios: sus parámetros congelados (exactos, para
    precargar el formulario) y los ítems pendientes que ningún escenario recalcula."""

    codigo: str
    proyecto: str
    moneda: str
    total: str
    parametros: dict[str, str]
    pendientes_base: list[PendienteRespuesta] = Field(default_factory=list)
