"""Rutas de listas de precios y su historial de cambios (UC-02)."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import select

from api.dependencias import SesionDep
from api.esquemas import CambioRespuesta, CargaListaRespuesta, ListaRespuesta
from core import models
from core.catalog import (
    PrecioLeido,
    cambios_precio,
    crear_lista_desde_archivo,
    insumos_desconocidos,
)

router = APIRouter(tags=["listas"])


@router.get("/listas-precios", response_model=list[ListaRespuesta])
def listar_listas_precios(sesion: SesionDep) -> list[ListaRespuesta]:
    """Listas de precios registradas, de la mas antigua a la mas reciente."""
    consulta = select(models.ListaPrecios).order_by(
        models.ListaPrecios.fecha_vigencia, models.ListaPrecios.id
    )
    return [ListaRespuesta.model_validate(lista) for lista in sesion.scalars(consulta)]


@router.post(
    "/listas-precios",
    response_model=CargaListaRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def cargar_lista_precios(
    sesion: SesionDep,
    archivo: Annotated[UploadFile, File()],
    nombre: Annotated[str, Form()],
    moneda: Annotated[str, Form()],
    fecha_vigencia: Annotated[date, Form()],
    dar_de_alta: Annotated[
        list[str] | None,
        Form(
            description="Descripciones, tal como vienen en el archivo, de los insumos "
            "desconocidos que se dan de alta (UC-02, flujo 2a); por defecto, ninguno"
        ),
    ] = None,
) -> CargaListaRespuesta:
    """Crea una lista de precios desde un archivo CSV o XLSX y confirma la transaccion (UC-02).

    Flujo 2a (INV-090): los insumos desconocidos que nombra `dar_de_alta` se dan de alta con
    codigo nuevo y su precio entra solo en esta lista; los demas desconocidos se ignoran. Una
    descripcion que no sea un desconocido del archivo (un insumo ya catalogado, una fila rechazada
    por unidad del flujo 2b o una que no esta en el archivo) es 422 sin escribir nada, igual que
    dos filas elegidas del mismo insumo con precios distintos. La respuesta separa los ignorados
    (2a) de los rechazados (2b): `ResumenLista.desconocidos` los trae juntos, y los ignorados son
    los que ofrece la vista previa `insumos_desconocidos`.
    """
    with tempfile.TemporaryDirectory() as directorio:
        ruta = Path(directorio) / archivo.filename
        ruta.write_bytes(archivo.file.read())
        candidatos = insumos_desconocidos(sesion, ruta)
        resumen = crear_lista_desde_archivo(
            sesion,
            ruta,
            nombre,
            moneda,
            fecha_vigencia,
            dar_de_alta=_elegidos(candidatos, dar_de_alta or (), ruta.name),
        )
    sesion.commit()
    return CargaListaRespuesta(
        lista=ListaRespuesta.model_validate(resumen.lista),
        desconocidos=[leido.descripcion for leido in resumen.desconocidos],
        dados_de_alta=[insumo.descripcion for insumo in resumen.dados_de_alta],
        ignorados=[leido.descripcion for leido in resumen.desconocidos if leido in candidatos],
        rechazados=[leido.descripcion for leido in resumen.desconocidos if leido not in candidatos],
    )


def _elegidos(
    candidatos: Sequence[PrecioLeido], descripciones: Sequence[str], archivo: str
) -> list[PrecioLeido]:
    """Las filas de la vista previa que nombran `descripciones` (todas las de cada una, si el
    archivo la repite: el nucleo decide si sus precios concuerdan). `ValueError` (422) si alguna
    descripcion no es un insumo desconocido de este archivo."""
    ajenas = [d for d in descripciones if all(c.descripcion != d for c in candidatos)]
    if ajenas:
        raise ValueError(
            f"{archivo}: {', '.join(repr(d) for d in ajenas)} no es un insumo desconocido de "
            "este archivo; solo se dan de alta los desconocidos del flujo 2a de UC-02 (un "
            "insumo catalogado o una fila rechazada por unidad no se dan de alta)"
        )
    return [c for c in candidatos if c.descripcion in descripciones]


@router.get("/cambios-precio", response_model=list[CambioRespuesta])
def listar_cambios_precio(
    sesion: SesionDep,
    insumo: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[CambioRespuesta]:
    """Historial de `CambioPrecio`, filtrable por descripcion de insumo y rango de fecha.

    La consulta vive una sola vez en `core.catalog.cambios_precio` (la misma que usa
    `ui/paginas/historico.py`); esta ruta solo serializa.
    """
    return [
        CambioRespuesta(
            insumo=cambio.insumo.descripcion,
            precio_anterior=str(cambio.precio_anterior),
            precio_nuevo=str(cambio.precio_nuevo),
            variacion=str(cambio.variacion),
            fecha=cambio.fecha,
        )
        for cambio in cambios_precio(sesion, insumo=insumo, desde=desde, hasta=hasta)
    ]
