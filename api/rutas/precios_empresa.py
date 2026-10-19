"""Precios de la empresa (UC-17 4-5; migracion de `ui/paginas/precios_empresa.py`, sesion 2b).

La logica vive en `aplicacion.precios_empresa` (la misma de la pantalla de Streamlit); aqui solo el
esquema HTTP. Rol `administrar_precios` (el administrador) en las cuatro rutas. Leer (`GET`)
acepta sesion o clave de API; las dos que escriben (`referencia` y `listas`) solo la sesion de
una cuenta: la clave recibe 403.

- `GET /v1/precios-empresa` -> `{bases, listas}`: las listas que pueden ser base y las de empresa.
- `POST /v1/precios-empresa/referencia` -> `{mensaje}`: carga la referencia MaPreX en Bs.
- `POST /v1/precios-empresa/listas` (multipart) -> 201 con la lista creada y los insumos que el
  catalogo no conoce. El archivo viene de fuera: solo `.csv` o `.xlsx`, tope de `TOPE_BYTES`, la
  guardia de `adapters.hoja_empresa` si es un libro, y nada de lo enviado vuelve en un error de
  validacion (`RutaSinEco`).
- `GET /v1/precios-empresa/listas/{id}/hallazgos?fecha=` -> R11 y R12 de la lista sola, en memoria.

Los mensajes son los de la pagina clasica. Un error de base no sale con su texto (lleva el SQL).
La busqueda de variaciones atipicas (RF-100) sigue solo en la pagina clasica: vive en
`ui/atipicos.py`, que la API no puede importar.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from api.admin_acceso import administrar
from api.archivos import guardar_subida
from api.dependencias import SesionDep
from api.rutas.listas import comprobar_libro_legible
from api.sesion_web import exigir_clave_o_sesion
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import precios_empresa as logica
from seguridad.permisos import Accion

MENSAJE_INVALIDO = "Los datos enviados no son válidos."
MENSAJE_CASO = "No se pudo leer o escribir el caso abierto."
MENSAJE_FALTA = "Elija la moneda de la lista y el archivo de precios: no tienen valor por defecto."
MENSAJE_FORMATO = "No se creo la lista: el archivo debe ser CSV o XLSX."
MENSAJE_TAMANO = "No se creo la lista: el archivo pesa mas del maximo permitido (20 MiB)."
MENSAJE_REFERENCIA_ILEGIBLE = (
    "No se cargo la referencia: no se pudo leer el archivo de la referencia."
)
AVISO_DESCONOCIDOS = "Estos insumos no estan en el catalogo y no entraron a la lista (UC-17 4a):"
NOTA_HALLAZGOS = "Sin version, el impacto es por unidad de insumo. Nada de esto se guarda."
SUFIJOS = (".csv", ".xlsx")
#: El tope real del cuerpo de cualquier peticion (`LimiteDeCuerpo`, api/proteccion.py): 20 MiB.
TOPE_BYTES = 20 * 2**20
LARGO_MAXIMO_DEL_MOTIVO = 500

#: Escribir es de una persona con rol: la clave de API recibe 403 (MEDIO-1).
SOLO_CUENTA = Depends(administrar(Accion.ADMINISTRAR_PRECIOS))

router = APIRouter(
    prefix="/v1/precios-empresa",
    tags=["precios-empresa"],
    dependencies=[Depends(exigir_clave_o_sesion(Accion.ADMINISTRAR_PRECIOS))],
    route_class=RutaSinEco,
)


class BaseRespuesta(BaseModel):
    id: int
    nombre: str
    moneda: str


class ListaEmpresaRespuesta(BaseModel):
    id: int
    nombre: str


class EstadoRespuesta(BaseModel):
    bases: list[BaseRespuesta]
    listas: list[ListaEmpresaRespuesta]


class MensajeRespuesta(BaseModel):
    mensaje: str


class ListaCreadaRespuesta(BaseModel):
    nombre: str
    propios: int
    desconocidos: list[str]
    mensaje: str
    aviso: str | None


class HallazgosRespuesta(BaseModel):
    columnas: list[str]
    filas: list[dict[str, str]]
    nota: str


@contextmanager
def _caso_legible() -> Iterator[None]:
    """El texto de un error de base lleva el SQL y sus parametros: no sale por la API."""
    try:
        yield
    except SQLAlchemyError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_CASO) from None


def _motivo(error: Exception) -> str:
    return str(error)[:LARGO_MAXIMO_DEL_MOTIVO]


@router.get("", response_model=EstadoRespuesta)
@sin_eco(MENSAJE_INVALIDO)
def estado(sesion: SesionDep) -> EstadoRespuesta:
    """Las listas que pueden ser base de la de una empresa y las listas de empresa del caso."""
    with _caso_legible():
        bases = logica.listas_base(sesion)
        listas = logica.listas_de_empresa(sesion)
    return EstadoRespuesta(
        bases=[BaseRespuesta(id=i, nombre=n, moneda=m) for i, n, m in bases],
        listas=[ListaEmpresaRespuesta(id=i, nombre=n) for i, n in listas],
    )


@router.post("/referencia", response_model=MensajeRespuesta, dependencies=[SOLO_CUENTA])
@sin_eco(MENSAJE_INVALIDO)
def cargar_referencia(sesion: SesionDep) -> MensajeRespuesta:
    """Carga la referencia MaPreX en Bs; una ya cargada no se duplica."""
    with _caso_legible():
        try:
            return MensajeRespuesta(mensaje=logica.cargar_referencia_maprex(sesion))
        except OSError:
            # El texto de un OSError lleva la ruta del servidor.
            raise HTTPException(422, MENSAJE_REFERENCIA_ILEGIBLE) from None
        except ValueError as error:
            raise HTTPException(422, f"No se cargo la referencia: {_motivo(error)}") from None


@router.post(
    "/listas",
    response_model=ListaCreadaRespuesta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[SOLO_CUENTA],
)
@sin_eco(MENSAJE_INVALIDO)
def crear_lista(
    sesion: SesionDep,
    base_id: Annotated[int, Form()],
    fecha: Annotated[date, Form()],
    empresa: Annotated[str, Form()] = "",
    rif: Annotated[str, Form()] = "",
    fuente: Annotated[str, Form()] = "",
    moneda: Annotated[str, Form()] = "",
    nombre: Annotated[str, Form()] = "",
    archivo: Annotated[UploadFile | None, File()] = None,
) -> ListaCreadaRespuesta:
    """UC-17 4: crea la lista de la empresa sobre una lista base con los precios del archivo.

    Empresa, RIF y fuente vacios llegan al nucleo, que los rechaza con su mensaje (como la pagina
    clasica). Todo o nada: ante cualquier error no queda nada escrito. Los insumos del archivo
    que el catalogo no conoce se informan y no se dan de alta (UC-17 4a).
    """
    if not moneda or archivo is None:
        raise HTTPException(422, MENSAJE_FALTA)
    if Path(archivo.filename or "").suffix.lower() not in SUFIJOS:
        raise HTTPException(422, MENSAJE_FORMATO)
    if len(archivo.file.read(TOPE_BYTES + 1)) > TOPE_BYTES:
        raise HTTPException(422, MENSAJE_TAMANO)
    archivo.file.seek(0)
    with _caso_legible():
        try:
            with tempfile.TemporaryDirectory() as directorio:
                ruta = guardar_subida(directorio, archivo)
                comprobar_libro_legible(ruta)
                resumen = logica.crear_lista(
                    sesion,
                    ruta,
                    empresa_nombre=empresa,
                    empresa_rif=rif,
                    base_id=base_id,
                    moneda=moneda,
                    fecha=fecha,
                    fuente=fuente,
                    nombre=nombre,
                )
        except ValueError as error:
            raise HTTPException(422, f"No se creo la lista: {_motivo(error)}") from None
    return ListaCreadaRespuesta(
        nombre=resumen.nombre,
        propios=resumen.propios,
        desconocidos=list(resumen.desconocidos),
        mensaje=f"Lista «{resumen.nombre}» creada con {resumen.propios} precios propios.",
        aviso=AVISO_DESCONOCIDOS if resumen.desconocidos else None,
    )


@router.get("/listas/{lista_id}/hallazgos", response_model=HallazgosRespuesta)
@sin_eco(MENSAJE_INVALIDO)
def hallazgos(lista_id: int, sesion: SesionDep, fecha: date | None = None) -> HallazgosRespuesta:
    """R11 y R12 de la lista sola a `fecha` (hoy si falta). No escribe nada."""
    with _caso_legible():
        if lista_id not in {i for i, _ in logica.listas_de_empresa(sesion)}:
            raise HTTPException(404, f"la lista {lista_id} no es una lista de empresa de este caso")
        filas = logica.hallazgos_de_lista(sesion, lista_id, fecha or date.today())
    return HallazgosRespuesta(
        columnas=list(logica.COLUMNAS_HALLAZGOS), filas=filas, nota=NOTA_HALLAZGOS
    )
