"""Esquemas de `/v1/hoja/borradores/{id}/plano` (T10, 3e-2): importar un plano a la hoja.

Contrato: `docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md`. Todo viaja como texto o entero
(ningun `float`); los cuerpos prohiben campos de mas. Topes (SUPUESTOS declarados, D-9): a lo sumo
5 000 alturas o circuitos por peticion y 500 caracteres por texto (id incluido).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from api.esquemas_hoja import ResumenHojaRespuesta, Texto500

#: Entradas por peticion de P3 y P4.
TOPE_ENTRADAS = 5000

Rev = Annotated[int, Field(strict=True, ge=0)]


class UnidadDelPlano(BaseModel):
    """P2: la unidad del dibujo con que se vuelve a leer el plano detenido."""

    model_config = ConfigDict(extra="forbid")

    rev: Rev
    unidades: Texto500


class AlturasDelPlano(BaseModel):
    """P3: id del ambiente pendiente -> su altura en metros (texto; coma o punto)."""

    model_config = ConfigDict(extra="forbid")

    rev: Rev
    alturas: Annotated[dict[Texto500, Texto500], Field(max_length=TOPE_ENTRADAS)]


CuatroTextos = Annotated[list[Texto500], Field(min_length=4, max_length=4)]


class CircuitosDelPlano(BaseModel):
    """P4: id del circuito supuesto -> [fase, neutro, tierra, puntos maximos] (texto)."""

    model_config = ConfigDict(extra="forbid")

    rev: Rev
    circuitos: Annotated[dict[Texto500, CuatroTextos], Field(max_length=TOPE_ENTRADAS)]


class FusionDelPlano(BaseModel):
    """P5: el `rev` que vio quien fusiona."""

    model_config = ConfigDict(extra="forbid")

    rev: Rev


class ConteoRespuesta(BaseModel):
    rotulo: str
    cantidad: int


class FilaInformeRespuesta(BaseModel):
    """Una linea del informe: tipo, lo que era en el plano, la fila de la hoja y que paso."""

    tipo: str
    referencia: str
    fila: str
    mensaje: str


class AlturaPendienteRespuesta(BaseModel):
    id: str
    nombre: str


class CircuitoSupuestoRespuesta(BaseModel):
    id: str
    fase: str
    neutro: str
    tierra: str
    puntos: str


class ImportacionRespuesta(BaseModel):
    """La importacion vigente del borrador (P1 a P4)."""

    estado: Literal["importada", "detenida", "rechazada"]
    archivo: str
    mensaje: str
    pide_unidad: bool
    unidades: list[str]
    conteos: list[ConteoRespuesta]
    informe: list[FilaInformeRespuesta]
    alturas_pendientes: list[AlturaPendienteRespuesta]
    circuitos_supuestos: list[CircuitoSupuestoRespuesta]
    aviso_pendientes: str | None


class ResumenDeFusionRespuesta(BaseModel):
    """`ResumenDeFusion`: el informe de la fusion contado una sola vez."""

    por_tipo: list[ConteoRespuesta]
    filas_por_tabla: list[ConteoRespuesta]
    origenes: int


class FusionRespuesta(BaseModel):
    """P5: el `rev` NUEVO (= `resumen.rev`), el resumen, el informe de la fusion y el mensaje."""

    rev: int
    resumen: ResumenHojaRespuesta
    fusion: ResumenDeFusionRespuesta
    informe: list[FilaInformeRespuesta]
    mensaje: str
