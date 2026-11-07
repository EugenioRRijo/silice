"""Esquemas de `/v1/vial`: los tramos viales de una versión (plan vial, Tarea 8).

Las cifras viajan como texto con punto decimal (la coma es cosa del front); un texto que no es un
decimal es 422 en la frontera (`a_tramos`). Las cantidades salen sin ceros de sobra y sin
redondear nada.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from adapters.vial.modelo import Capa, Demarcacion, Tramo
from aplicacion.vial import (
    MAX_CAPAS,
    MAX_LINEAS_DE_DEMARCACION,
    MAX_TRAMOS,
    CantidadVial,
    RastroDeGuardado,
    texto_decimal,
)

#: Los topes de tramos, capas y líneas (`MAX_*`) viven en `aplicacion.vial`: los aplica también
#: la importación del CSV (Tarea 8b).
LARGO_CIFRA = 40
LARGO_FUENTE = 300

#: Solo cifras 0-9 y un punto decimal, con un «-» opcional que el dominio rechaza con su texto.
_CIFRA = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")

Cifra = Annotated[str, Field(max_length=LARGO_CIFRA)]


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapaEntrada(_Estricto):
    tipo: Annotated[str, Field(max_length=40)]
    espesor_m: Cifra | None = None
    densidad_t_m3: Cifra | None = None
    dosis_l_m2: Cifra | None = None
    #: Porcentaje de asfalto de la mezcla de la carpeta o del bacheo (Tarea 16b; lo compara VR2).
    asfalto_pct: Cifra | None = None
    #: F5 vial, tarea 1: esponjamiento del fresado, limpieza de un riego y la otra medición.
    esponjamiento: Cifra | None = None
    limpieza: StrictBool = False
    medicion: Annotated[str, Field(max_length=10)] | None = None


class DemarcacionEntrada(_Estricto):
    tipo: Annotated[str, Field(max_length=40)]
    lineas: StrictInt
    #: F5 vial, tarea 1: el área de cada elemento de superficie y los captafaros de una línea.
    area_m2: Cifra | None = None
    captafaros: StrictInt | None = None


class TramoEntrada(_Estricto):
    id: Annotated[str, Field(max_length=200)]
    progresiva_ini_km: Cifra
    progresiva_fin_km: Cifra
    ancho_m: Cifra
    distancia_planta_km: Cifra | None = None
    #: F5 vial, tarea 2: «banda» si la obra mide el transporte en t por banda; vacío, en t·km.
    transporte: Annotated[str, Field(max_length=10)] | None = None
    capas: Annotated[list[CapaEntrada], Field(max_length=MAX_CAPAS)]
    demarcacion: Annotated[
        list[DemarcacionEntrada], Field(max_length=MAX_LINEAS_DE_DEMARCACION)
    ] = []


class TramosEntrada(_Estricto):
    tramos: Annotated[list[TramoEntrada], Field(max_length=MAX_TRAMOS)]
    fuente: Annotated[str, Field(max_length=LARGO_FUENTE)] = ""


def _cifra(tramo: str, campo: str, texto: str | None) -> Decimal | None:
    if texto is None:
        return None
    if _CIFRA.fullmatch(texto) is None:
        raise ValueError(
            f"tramo {tramo}: {campo} debe ser un número con punto decimal (por ejemplo 7.3), "
            f"no {texto[:20]!r}"
        )
    return Decimal(texto)


def _obligatoria(tramo: str, campo: str, texto: str) -> Decimal:
    valor = _cifra(tramo, campo, texto)
    if valor is None:  # no ocurre: el esquema la exige como texto
        raise ValueError(f"tramo {tramo}: falta {campo}")
    return valor


def a_tramos(entrada: Sequence[TramoEntrada]) -> list[Tramo]:
    """Los `Tramo` de la entrada. `ValueError` con el texto del dominio (y el id del tramo) si una
    cifra no es un decimal o un tramo no cumple las reglas de `adapters.vial`."""
    tramos = []
    for t in entrada:
        capas = tuple(
            Capa(
                c.tipo,
                _cifra(t.id, "espesor_m", c.espesor_m),
                _cifra(t.id, "densidad_t_m3", c.densidad_t_m3),
                _cifra(t.id, "dosis_l_m2", c.dosis_l_m2),
                _cifra(t.id, "asfalto_pct", c.asfalto_pct),
                esponjamiento=_cifra(t.id, "esponjamiento", c.esponjamiento),
                limpieza=c.limpieza,
                medicion=c.medicion,
            )
            for c in t.capas
        )
        tramos.append(
            Tramo(
                t.id,
                _obligatoria(t.id, "progresiva_ini_km", t.progresiva_ini_km),
                _obligatoria(t.id, "progresiva_fin_km", t.progresiva_fin_km),
                _obligatoria(t.id, "ancho_m", t.ancho_m),
                capas,
                tuple(
                    Demarcacion(
                        d.tipo,
                        d.lineas,
                        area_m2=_cifra(t.id, "area_m2", d.area_m2),
                        captafaros=d.captafaros,
                    )
                    for d in t.demarcacion
                ),
                _cifra(t.id, "distancia_planta_km", t.distancia_planta_km),
                t.transporte,
            )
        )
    return tramos


def _nulo(valor: object) -> bool:
    """Un dato opcional de F5 que el tramo no declara (`None` o `False`): no viaja."""
    return valor is None or valor is False


class CapaRespuesta(BaseModel):
    tipo: str
    espesor_m: str | None
    densidad_t_m3: str | None
    dosis_l_m2: str | None
    asfalto_pct: str | None = None
    # F5 vial: solo viajan si la capa los declara, así la respuesta de un tramo de antes no cambia
    esponjamiento: str | None = Field(default=None, exclude_if=_nulo)
    limpieza: bool = Field(default=False, exclude_if=_nulo)
    medicion: str | None = Field(default=None, exclude_if=_nulo)


class DemarcacionRespuesta(BaseModel):
    tipo: str
    lineas: int
    area_m2: str | None = Field(default=None, exclude_if=_nulo)
    captafaros: int | None = Field(default=None, exclude_if=_nulo)


class TramoRespuesta(BaseModel):
    id: str
    progresiva_ini_km: str
    progresiva_fin_km: str
    ancho_m: str
    distancia_planta_km: str | None
    transporte: str | None = Field(default=None, exclude_if=_nulo)
    capas: list[CapaRespuesta]
    demarcacion: list[DemarcacionRespuesta]


class CantidadRespuesta(BaseModel):
    tramo: str
    codigo: str
    descripcion: str
    unidad: str
    cantidad: str
    origen_id: str
    regla: str


class RastroDeTramosRespuesta(BaseModel):
    usuario: str
    fecha_hora: str
    fuente: str


class TramosRespuesta(BaseModel):
    proyecto: str
    version: str
    editable: bool
    bloqueo: str | None
    heredados_de: str | None
    guardado: RastroDeTramosRespuesta | None
    tramos: list[TramoRespuesta]
    cantidades: list[CantidadRespuesta]


class ObrasViales(BaseModel):
    obras: list[int]


class LlevarTramos(_Estricto):
    """La obra (su código de `/v1/proyectos` o su nombre) y la versión (código) cuyos tramos se
    llevan al presupuesto: la que muestra la pantalla «Tramos»."""

    proyecto: Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    version: Annotated[str, Field(strict=True, min_length=1, max_length=40)]


class TramosLlevados(BaseModel):
    """El borrador de la Hoja de la obra, con los renglones de tramo ya puestos (sin guardar)."""

    borrador_id: str
    renglones: int
    #: La versión cuyos tramos se llevaron (la del borrador).
    version: str


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def tramo_a_respuesta(t: Tramo) -> TramoRespuesta:
    return TramoRespuesta(
        id=t.id,
        progresiva_ini_km=format(t.progresiva_ini_km, "f"),
        progresiva_fin_km=format(t.progresiva_fin_km, "f"),
        ancho_m=format(t.ancho_m, "f"),
        distancia_planta_km=_texto(t.distancia_planta_km),
        transporte=t.transporte,
        capas=[
            CapaRespuesta(
                tipo=c.tipo,
                espesor_m=_texto(c.espesor_m),
                densidad_t_m3=_texto(c.densidad_t_m3),
                dosis_l_m2=_texto(c.dosis_l_m2),
                asfalto_pct=_texto(c.asfalto_pct),
                esponjamiento=_texto(c.esponjamiento),
                limpieza=c.limpieza,
                medicion=c.medicion,
            )
            for c in t.capas
        ],
        demarcacion=[
            DemarcacionRespuesta(
                tipo=d.tipo, lineas=d.lineas, area_m2=_texto(d.area_m2), captafaros=d.captafaros
            )
            for d in t.demarcacion
        ],
    )


def cantidad_a_respuesta(c: CantidadVial) -> CantidadRespuesta:
    return CantidadRespuesta(
        tramo=c.tramo,
        codigo=c.codigo,
        descripcion=c.descripcion,
        unidad=c.unidad,
        cantidad=texto_decimal(c.cantidad),
        origen_id=c.origen_id,
        regla=c.regla,
    )


def rastro_a_respuesta(g: RastroDeGuardado | None) -> RastroDeTramosRespuesta | None:
    if g is None:
        return None
    return RastroDeTramosRespuesta(
        usuario=g.usuario, fecha_hora=g.fecha_hora.isoformat(timespec="seconds"), fuente=g.fuente
    )
