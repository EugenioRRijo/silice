"""Rutas de listas de precios y su historial de cambios (UC-02)."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Annotated

import openpyxl
from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from adapters.hoja_empresa.guardia import ArchivoRechazado, verificar_archivo
from api.acceso import EDITAR, LEER
from api.archivos import guardar_subida
from api.dependencias import SesionDep
from api.esquemas import CambioRespuesta, CargaListaRespuesta, ListaRespuesta
from api.esquemas_ola2 import InsumoDesconocidoRespuesta, VistaPreviaRespuesta
from aplicacion.actualizacion import nombrar
from core import models
from core.catalog import (
    PrecioLeido,
    cambios_precio,
    crear_lista_desde_archivo,
    insumos_desconocidos,
)
from core.catalog.precios import SUFIJOS_EXCEL
from core.verification.texto import normalizar_texto

router = APIRouter(tags=["listas"])


@router.get("/listas-precios", response_model=list[ListaRespuesta], dependencies=LEER)
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
    dependencies=EDITAR,
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
            description="Descripciones de los insumos desconocidos del archivo que se dan de "
            "alta (UC-02, flujo 2a), comparadas sin distinguir mayusculas, tildes ni espacios; "
            "por defecto, ninguno"
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
        ruta = guardar_subida(directorio, archivo)
        comprobar_libro_legible(ruta)
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


@router.post(
    "/listas-precios/vista-previa", response_model=VistaPreviaRespuesta, dependencies=EDITAR
)
def vista_previa_de_lista(
    sesion: SesionDep, archivo: Annotated[UploadFile, File()]
) -> VistaPreviaRespuesta:
    """UC-02, flujo 2a: los insumos del archivo que el catálogo no conoce y se pueden dar de alta
    (`insumos_desconocidos`), antes de revalorar. No escribe nada.

    Un archivo o una base que no se pueden leer no ofrecen nada y traen su `motivo`: el mismo fallo
    sale con su mensaje al revalorar, que es donde se informan los errores de UC-02.
    """
    with tempfile.TemporaryDirectory() as directorio:
        ruta = guardar_subida(directorio, archivo)
        try:
            comprobar_libro_legible(ruta)
            ofrecidos = insumos_desconocidos(sesion, ruta)
        except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
            return VistaPreviaRespuesta(desconocidos=[], motivo=str(error))
    return VistaPreviaRespuesta(
        desconocidos=[
            InsumoDesconocidoRespuesta(
                descripcion=leido.descripcion,
                tipo=leido.tipo.value,
                unidad=leido.unidad,
                precio=str(leido.precio),
                etiqueta=nombrar(leido),
            )
            for leido in ofrecidos
        ]
    )


def comprobar_libro_legible(ruta: Path) -> None:
    """`ValueError` (422) con el nombre del archivo si `ruta` es un libro de Excel que openpyxl no
    puede abrir: bytes que no son un zip (`zipfile.BadZipFile`), un zip sin las partes de un libro
    (`KeyError`, que el manejador de `LookupError` responderia como 404) o un archivo truncado.

    Ronda 1 de la pista A (H1): sin esta comprobacion, `POST /listas-precios` y
    `POST /presupuestos/importar` respondian 500 ante un .xlsx corrupto. Se abre el libro antes de
    llamar al nucleo, asi que cualquier fallo de esta apertura es del archivo y no se confunde con
    un error del catalogo; la traduccion de fondo, en el lector del nucleo, queda para GC6. Un
    archivo de otro sufijo no se toca: su rechazo es del nucleo.
    """
    if ruta.suffix.lower() not in SUFIJOS_EXCEL:
        return
    try:
        verificar_archivo(ruta.read_bytes(), ruta.name)
    except ArchivoRechazado as error:
        raise ValueError(f"{ruta.name}: no se puede leer como libro de Excel ({error})") from error
    # El flujo lo abre y lo cierra esta funcion: si openpyxl falla a mitad, en Windows dejaria el
    # archivo abierto y el directorio temporal de la ruta no se podria borrar.
    with ruta.open("rb") as flujo:
        try:
            openpyxl.load_workbook(flujo, read_only=True).close()
        except Exception as error:
            raise ValueError(
                f"{ruta.name}: no se puede leer como libro de Excel "
                f"({type(error).__name__}: {error})"
            ) from error


def _elegidos(
    candidatos: Sequence[PrecioLeido], descripciones: Sequence[str], archivo: str
) -> list[PrecioLeido]:
    """Las filas de la vista previa que nombran `descripciones`. `ValueError` (422) si alguna
    descripcion no es un insumo desconocido de este archivo.

    Se compara con `normalizar_texto`, la identidad del nucleo (`core.catalog.precios`): una
    descripcion elige **todas** las filas de su identidad, con cualquier grafia (mayusculas,
    tildes, espacios), y el nucleo decide si sus precios concuerdan (una sola alta) o no (422).
    Elegir solo la grafia exacta dejaria fuera una fila de la misma identidad, que luego
    sobrescribiria en silencio el precio del alta (ronda 1 de la pista A, H2).
    """
    elegidas = {normalizar_texto(d) for d in descripciones}
    disponibles = {normalizar_texto(c.descripcion) for c in candidatos}
    ajenas = [d for d in descripciones if normalizar_texto(d) not in disponibles]
    if ajenas:
        raise ValueError(
            f"{archivo}: {', '.join(repr(d) for d in ajenas)} no es un insumo desconocido de "
            "este archivo; solo se dan de alta los desconocidos del flujo 2a de UC-02 (un "
            "insumo catalogado o una fila rechazada por unidad no se dan de alta)"
        )
    return [c for c in candidatos if normalizar_texto(c.descripcion) in elegidas]


@router.get("/cambios-precio", response_model=list[CambioRespuesta], dependencies=LEER)
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
