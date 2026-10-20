"""Esquema de las variaciones atípicas de precio (RF-100) para la API.

Lo comparten «Precios de la empresa» (`GET /v1/precios-empresa/listas/{id}/atipicos`) y la pestaña
Precios de la hoja (`GET /v1/hoja/precios/atipicos`): una sola copia, para que las rutas no se
importen entre sí. La lógica es `aplicacion.atipicos`, la misma de la página clásica; los avisos
van sin escapar (aquí no hay Markdown) y los hallazgos, por partes, en `variaciones`.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from aplicacion import atipicos as busqueda_atipica


class AvisoAtipicos(BaseModel):
    """Un aviso de la busqueda, con el nivel de la pagina clasica (`info` o `success`)."""

    nivel: Literal["info", "success"]
    texto: str


class VariacionAtipicaRespuesta(BaseModel):
    """Un hallazgo de RF-100: `porcentaje` es la variacion en por ciento con dos decimales, como
    texto (la de la descripcion), y `porcentaje_exacto` la misma sin redondear (el exacto a la
    vista); `desde` y `hasta`, las fechas de los dos precios."""

    insumo: str
    porcentaje: str
    porcentaje_exacto: str
    desde: date
    hasta: date
    severidad: str
    descripcion: str


class AtipicosRespuesta(BaseModel):
    """`disponible` es falso sin el extra `ml`: no se busco nada y un aviso lo dice."""

    disponible: bool
    avisos: list[AvisoAtipicos]
    variaciones: list[VariacionAtipicaRespuesta]


def atipicos_a_respuesta(busqueda: busqueda_atipica.BusquedaAtipicos | None) -> AtipicosRespuesta:
    """La busqueda (o `None` sin el extra `ml`) como respuesta de la API."""
    return AtipicosRespuesta(
        disponible=busqueda is not None,
        avisos=[
            AvisoAtipicos(nivel=nivel, texto=texto)
            for nivel, texto in busqueda_atipica.avisos_generales(busqueda)
        ],
        variaciones=[
            VariacionAtipicaRespuesta(
                insumo=v.insumo,
                porcentaje=v.porcentaje,
                porcentaje_exacto=v.porcentaje_exacto,
                desde=v.desde,
                hasta=v.hasta,
                severidad=v.severidad.name,
                descripcion=v.descripcion,
            )
            for v in busqueda_atipica.variaciones_atipicas(busqueda)
        ],
    )
