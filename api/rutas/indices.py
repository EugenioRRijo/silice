"""`/v1/indices/*`: «Índices del BCV» por HTTP (migración; UC-17 pasos 1-3, RM-3).

Es `ui/paginas/indices.py` hecha servicio sobre `aplicacion.indices` (la misma lógica que usa
Streamlit; los mensajes de error son los suyos). Todas las rutas exigen `ADMINISTRAR_PRECIOS` (rol
administrador) con sesión o clave de API y trabajan sobre el caso de la sesión (`SesionDep`):

- `GET /contexto` -> los tipos de archivo, las periodicidades, la unidad por defecto, las
  extensiones, si este equipo lee `.xls` (falta el extra `bcv` si no) y el responsable.
- `POST /leer` (multipart) -> el informe previo del archivo: filas, series con su rango, rechazos
  y advertencias. **No escribe nada.**
- `POST /confirmar` (multipart) -> vuelve a leer el archivo, comprueba que sea el que se leyó
  (`huella`) y guarda todas sus series en una transacción; dice qué hizo con cada una.

Sin estado en el servidor: el informe no se guarda entre «leer» y «confirmar»; el cliente reenvía
el archivo y la ruta lo vuelve a leer, así que lo que se guarda es siempre lo que el archivo dice.
El contenido de lo que se sube nunca se confía: el nombre se reduce a su último componente válido
en Windows, el tamaño tiene tope, un `.xlsx` pasa por la guardia (`adapters.hoja_empresa.guardia`)
antes del lector del BCV, el archivo vive en una carpeta temporal y un 422 de forma no repite lo
enviado (`RutaSinEco`). Los valores de los índices no viajan en la respuesta: solo recuentos y
rangos de fechas, como la pantalla clásica. Leer (`/contexto`, `/leer`) acepta sesión o clave de
API; confirmar solo la sesión de una cuenta con el rol (la clave recibe 403) y el responsable
es SIEMPRE la persona de la sesión (RF-82), nunca el formulario.
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from adapters.bcv.informe import InformeImportacion
from adapters.bcv.libro import LIMITE_BYTES
from adapters.hoja_empresa.guardia import ArchivoRechazado, verificar_archivo
from api.admin_acceso import administrar
from api.archivos import nombre_seguro
from api.dependencias import SesionDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_eco import RutaSinEco
from aplicacion import indices as logica
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Los datos enviados no son válidos: "
    "revise el tipo de archivo, el archivo y la fecha de descarga."
)
MENSAJE_TIPO = "Tipo de archivo no reconocido; se espera tasa, inpc o csv."
MENSAJE_EXTENSION = "Solo se aceptan archivos .xls, .xlsx o .csv."
MENSAJE_SIN_NOMBRE = "El archivo subido no trae un nombre utilizable"
MENSAJE_DEFINICIONES = "Las definiciones de las series no tienen la forma esperada."
MENSAJE_HUELLA = "El archivo no es el que se leyó; léalo de nuevo antes de confirmar."
EXTENSIONES = [".xls", ".xlsx", ".csv"]
MAXIMO_RECHAZOS = 500  # el informe cuenta todos; la lista que viaja se acota
MAXIMO_MENSAJE = 500
MAXIMO_DEFINICIONES = 50
CAMPOS_DEFINICION = ("serie", "nombre", "organismo", "unidad", "periodicidad")
SIN_CACHE = {"Cache-Control": "no-store"}

ADMINISTRAR = Depends(exigir_clave_o_sesion(Accion.ADMINISTRAR_PRECIOS))
#: Escribir es de una persona con rol: la clave de API recibe 403 (MEDIO-1).
SOLO_CUENTA = Depends(administrar(Accion.ADMINISTRAR_PRECIOS))


class _RutaIndices(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(
    prefix="/v1/indices", tags=["indices"], route_class=_RutaIndices, dependencies=[ADMINISTRAR]
)


# --- Esquemas -----------------------------------------------------------------------------


class TipoRespuesta(BaseModel):
    id: str
    rotulo: str


class ContextoRespuesta(BaseModel):
    tipos: list[TipoRespuesta]
    periodicidades: list[str]
    unidad_por_defecto: str
    extensiones: list[str]
    lee_xls: bool
    responsable: str


class SerieRespuesta(BaseModel):
    clave: str
    valores: int
    desde: str
    hasta: str


class RechazoRespuesta(BaseModel):
    lugar: str
    motivo: str


class InformeRespuesta(BaseModel):
    archivo: str
    huella: str
    fuente: str
    fecha_descarga: date
    filas_leidas: int
    filas_rechazadas: int
    provisionales: int
    series: list[SerieRespuesta]
    rechazos: list[RechazoRespuesta]
    rechazos_omitidos: int
    advertencias: list[str]


class ConfirmacionRespuesta(BaseModel):
    mensajes: list[str]


# --- Ayudas -------------------------------------------------------------------------------


def _lee_xls() -> bool:
    """¿Está `xlrd` (extra `bcv`)? Sin él, un `.xls` no se puede leer."""
    from importlib.util import find_spec

    try:
        return find_spec("xlrd") is not None
    except ValueError:  # un módulo sin __spec__ en sys.modules: está importado
        return True


def _corto(error: object) -> str:
    texto = str(error)
    return texto if len(texto) <= MAXIMO_MENSAJE else texto[: MAXIMO_MENSAJE - 1] + "…"


def _no_importa(motivo: object) -> HTTPException:
    return HTTPException(422, f"No se importo nada: {_corto(motivo)}")


def _leer_archivo(
    archivo: UploadFile, tipo: str, fuente: str, fecha_descarga: date
) -> InformeImportacion:
    """Guarda la subida en una carpeta temporal y la lee. 422 con los mensajes de la pantalla."""
    if tipo not in logica.TIPOS:
        raise HTTPException(422, MENSAJE_TIPO)
    try:
        nombre = nombre_seguro(archivo.filename)
    except ValueError:
        raise HTTPException(422, MENSAJE_SIN_NOMBRE) from None
    if Path(nombre).suffix.lower() not in EXTENSIONES:
        raise HTTPException(422, MENSAJE_EXTENSION)
    archivo.file.seek(0, 2)
    tamano = archivo.file.tell()
    archivo.file.seek(0)
    if tamano > LIMITE_BYTES:
        raise _no_importa(
            f"{nombre}: pesa {tamano / 2**20:.1f} MB; el limite es {LIMITE_BYTES // 2**20} MB"
        )
    contenido = archivo.file.read(LIMITE_BYTES + 1)
    try:
        if nombre.lower().endswith(".xlsx"):
            verificar_archivo(contenido, nombre)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / nombre
            ruta.write_bytes(contenido)
            return logica.leer(ruta, tipo, fuente=fuente, fecha_descarga=fecha_descarga)
    except ArchivoRechazado as error:
        raise _no_importa(error) from None
    except ValueError as error:  # `FormatoNoReconocido` es `ValueError` (UC-17 2a)
        raise _no_importa(error) from None


def _definiciones(texto: str):
    """Las definiciones que declara quien importa un CSV, de su JSON. 422 sin eco si no tiene la
    forma `[{serie, nombre, organismo, unidad, periodicidad}, ...]` (todo texto)."""
    try:
        filas = json.loads(texto)
    except ValueError:
        raise HTTPException(422, MENSAJE_DEFINICIONES) from None
    if (
        not isinstance(filas, list)
        or len(filas) > MAXIMO_DEFINICIONES
        or not all(
            isinstance(f, dict)
            and set(f) == set(CAMPOS_DEFINICION)
            and all(isinstance(f[c], str) for c in CAMPOS_DEFINICION)
            for f in filas
        )
    ):
        raise HTTPException(422, MENSAJE_DEFINICIONES)
    return filas


def _informe_de(informe: InformeImportacion) -> InformeRespuesta:
    rechazos = logica.filas_del_informe(informe)
    return InformeRespuesta(
        archivo=informe.archivo,
        huella=informe.huella,
        fuente=informe.fuente,
        fecha_descarga=informe.fecha_descarga,
        filas_leidas=informe.filas_leidas,
        filas_rechazadas=informe.filas_rechazadas,
        provisionales=informe.provisionales,
        series=[
            SerieRespuesta(
                clave=s["serie"], valores=s["valores"], desde=s["desde"], hasta=s["hasta"]
            )
            for s in logica.resumen_de_series(informe)
        ],
        rechazos=[
            RechazoRespuesta(lugar=r["Lugar"], motivo=r["Motivo"])
            for r in rechazos[:MAXIMO_RECHAZOS]
        ],
        rechazos_omitidos=max(0, len(rechazos) - MAXIMO_RECHAZOS),
        advertencias=list(informe.advertencias),
    )


# --- Rutas --------------------------------------------------------------------------------


@router.get("/contexto", response_model=ContextoRespuesta)
def contexto(activa: Annotated[SesionActiva | None, ADMINISTRAR]) -> ContextoRespuesta:
    return ContextoRespuesta(
        tipos=[TipoRespuesta(id=t, rotulo=logica.ROTULOS_TIPO[t]) for t in logica.TIPOS],
        periodicidades=list(logica.PERIODICIDADES),
        unidad_por_defecto=logica.UNIDAD_INDICE_BS,
        extensiones=EXTENSIONES,
        lee_xls=_lee_xls(),
        responsable="" if activa is None else activa.usuario,
    )


@router.post("/leer", response_model=InformeRespuesta)
def leer(
    tipo: Annotated[str, Form(max_length=20)],
    archivo: Annotated[UploadFile, File()],
    fecha_descarga: Annotated[date, Form()],
    fuente: Annotated[str, Form(max_length=500)] = "",
) -> InformeRespuesta:
    """UC-17 1-2: lee el archivo y muestra lo que se importaría. No escribe nada."""
    return _informe_de(_leer_archivo(archivo, tipo, fuente, fecha_descarga))


@router.post("/confirmar", response_model=ConfirmacionRespuesta)
def confirmar(
    sesion: SesionDep,
    activa: Annotated[SesionActiva, SOLO_CUENTA],
    tipo: Annotated[str, Form(max_length=20)],
    archivo: Annotated[UploadFile, File()],
    fecha_descarga: Annotated[date, Form()],
    fuente: Annotated[str, Form(max_length=500)] = "",
    definiciones: Annotated[str, Form(max_length=20000)] = "[]",
    huella: Annotated[str, Form(max_length=64)] = "",
) -> ConfirmacionRespuesta:
    """UC-17 3: guarda las series del archivo con su huella; el mismo archivo dos veces no
    escribe nada. Todo o nada."""
    filas = _definiciones(definiciones)
    informe = _leer_archivo(archivo, tipo, fuente, fecha_descarga)
    if huella and huella != informe.huella:
        raise HTTPException(409, MENSAJE_HUELLA)
    quien = activa.usuario  # RF-82: siempre la persona de la sesion
    try:
        declaradas = logica.definiciones_desde_filas(filas) if tipo == "csv" else None
        mensajes = logica.confirmar(
            sesion, informe, responsable=quien, definiciones_csv=declaradas, ahora=ahora()
        )
    except ValueError as error:
        raise HTTPException(422, f"No se guardo nada: {_corto(error)}") from None
    except SQLAlchemyError as error:
        motor = getattr(error, "orig", None)
        # `orig` es el mensaje del motor, sin el SQL ni sus parámetros.
        raise HTTPException(
            503,
            f"No se pudo escribir en el caso: {_corto(motor or 'error de base')}",
        ) from None
    return ConfirmacionRespuesta(mensajes=mensajes)
