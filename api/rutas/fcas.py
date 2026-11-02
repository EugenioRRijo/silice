"""`/v1/fcas`: el FCAS calculado por componentes (Tarea 17 del plan vial).

- `GET /componentes` → los componentes por defecto (con su base legal y si piden cotejo), los días
  calendario del período (365) y el FCAS de una versión sin cambios (`fcas_version`, el de
  `ParametrosCosto`, 6.00).
- `POST /calcular` `{dias_calendario, dias_trabajados, componentes: [{id, nombre, base, valor,
  fuente}], fcas_version?}` → 200 con el `fcas` (fracción, 4 decimales), `porcentaje` (2),
  `multiplicador` (4), el `fcas_por_dias`, los `dias_pagados`, el `desglose`, lo que está
  `a_cotejar` y, si se mandó `fcas_version`, el de la versión al lado (`version`). Todo texto con
  punto decimal; un `bono_alimentacion` es 422.

Es una cuenta pura (`aplicacion.fcas`): no toca la base ni la carpeta abierta y **no aplica
nada**. El FCAS de una versión se cambia con la edición de parámetros de la Hoja, que ya existe.

Acceso: la clave de API o la sesión de cualquier rol (es una calculadora, como «Acerca de»); el
POST, como todo método que escribe con cookie, exige `X-Silice-CSRF` y `Origin`. Las cifras entran
como **texto con punto decimal** (la coma es cosa del front); un texto que no es decimal o un
valor imposible es 422 con `{"detalle": ...}`."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictStr

from api.sesion_web import exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from aplicacion.fcas import (
    COMPONENTES_FCAS,
    DESGLOSE_DIAS_NO_TRABAJADOS,
    DIAS_CALENDARIO,
    ComponenteFCAS,
    calcular_fcas,
)
from core.contracts import ParametrosCosto

CUALQUIER_ROL = exigir_clave_o_sesion(None)

router = APIRouter(
    prefix="/v1/fcas",
    tags=["fcas"],
    dependencies=[Depends(CUALQUIER_ROL)],
    route_class=RutaSinCache,
)

__all__ = ["CUALQUIER_ROL", "router"]

#: Un decimal con punto, sin exponente, NaN ni infinito (lo mismo que el resto de la API).
_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_NOMBRE_DEL_PRIMER_RENGLON = "Días pagados sin trabajar (descansos, feriados, permisos)"
_MAXIMO_DE_COMPONENTES = 50


class ComponenteFcasEntrada(BaseModel):
    id: StrictStr = Field(min_length=1, max_length=60)
    nombre: StrictStr = Field(min_length=1, max_length=200)
    base: StrictStr = Field(max_length=20)  # "dias" o "porcentaje"
    valor: StrictStr  # decimal con punto: días de salario, o por ciento del salario pagado
    fuente: StrictStr = Field(max_length=600)


class CalculoFcasEntrada(BaseModel):
    dias_calendario: StrictStr  # decimal con punto
    dias_trabajados: StrictStr  # decimal con punto
    componentes: list[ComponenteFcasEntrada] = Field(max_length=_MAXIMO_DE_COMPONENTES)
    fcas_version: StrictStr | None = None  # el de la versión que se compara, fracción con punto


class ComponenteFcasRespuesta(BaseModel):
    id: str
    nombre: str
    base: str
    valor: str
    fuente: str
    a_cotejar: bool


class ComponentesFcasRespuesta(BaseModel):
    dias_calendario: str
    fcas_version: str
    componentes: list[ComponenteFcasRespuesta]


class RenglonFcas(BaseModel):
    id: str
    nombre: str
    aporte: str  # fracción del FCAS, 4 decimales


class AvisoFcas(BaseModel):
    id: str
    nombre: str


class VersionFcas(BaseModel):
    fcas: str
    porcentaje: str
    multiplicador: str


class CalculoFcasRespuesta(BaseModel):
    fcas: str  # fracción: 0.7863 es 78,63 % y el motor aplica sueldo × (1 + fcas)
    fcas_por_dias: str
    dias_pagados: str
    porcentaje: str  # dos decimales
    multiplicador: str  # 1 + fcas, cuatro decimales
    desglose: list[RenglonFcas]
    a_cotejar: list[AvisoFcas]
    version: VersionFcas | None


def _decimal(nombre: str, texto: str) -> Decimal:
    if not _DECIMAL.fullmatch(texto.strip()):
        raise HTTPException(
            status_code=422,
            detail=f"{nombre}: escriba un número decimal con punto, por ejemplo 217.28.",
        )
    return Decimal(texto.strip())


def _redondeado(valor: Decimal, lugares: int) -> str:
    return str(valor.quantize(Decimal(1).scaleb(-lugares), rounding=ROUND_HALF_UP))


def _de_la_version(texto: str) -> VersionFcas:
    fcas = _decimal("fcas_version", texto)
    if fcas < 0:
        raise HTTPException(status_code=422, detail="fcas_version: no puede ser negativo.")
    escrito = texto.strip()
    lugares = max(
        2, len(escrito.partition(".")[2])
    )  # el multiplicador conserva los decimales escritos
    return VersionFcas(
        fcas=escrito,
        porcentaje=_redondeado(fcas * 100, 2),
        multiplicador=_redondeado(1 + fcas, lugares),
    )


@router.get("/componentes", response_model=ComponentesFcasRespuesta)
def componentes_por_defecto() -> ComponentesFcasRespuesta:
    return ComponentesFcasRespuesta(
        dias_calendario=str(DIAS_CALENDARIO),
        fcas_version=str(ParametrosCosto().fcas),
        componentes=[
            ComponenteFcasRespuesta(
                id=c.id,
                nombre=c.nombre,
                base=c.base,
                valor=str(c.valor),
                fuente=c.fuente,
                a_cotejar=c.a_cotejar,
            )
            for c in COMPONENTES_FCAS
        ],
    )


@router.post("/calcular", response_model=CalculoFcasRespuesta)
def calcular(cuerpo: CalculoFcasEntrada) -> CalculoFcasRespuesta:
    calendario = _decimal("dias_calendario", cuerpo.dias_calendario)
    trabajados = _decimal("dias_trabajados", cuerpo.dias_trabajados)
    version = None if cuerpo.fcas_version is None else _de_la_version(cuerpo.fcas_version)
    try:
        componentes = [
            ComponenteFCAS(c.id, c.nombre, c.base, _decimal(f"valor de {c.id}", c.valor), c.fuente)
            for c in cuerpo.componentes
        ]
        resultado = calcular_fcas(componentes, calendario, trabajados)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    nombres = {c.id: c.nombre for c in componentes} | {
        DESGLOSE_DIAS_NO_TRABAJADOS: _NOMBRE_DEL_PRIMER_RENGLON
    }
    return CalculoFcasRespuesta(
        fcas=_redondeado(resultado.fcas, 4),
        fcas_por_dias=_redondeado(resultado.fcas_por_dias, 4),
        dias_pagados=str(resultado.dias_pagados),
        porcentaje=_redondeado(resultado.fcas * 100, 2),
        multiplicador=_redondeado(1 + resultado.fcas, 4),
        desglose=[
            RenglonFcas(id=i, nombre=nombres[i], aporte=_redondeado(aporte, 4))
            for i, aporte in resultado.desglose
        ],
        a_cotejar=[AvisoFcas(id=i, nombre=nombres[i]) for i in resultado.a_cotejar],
        version=version,
    )
