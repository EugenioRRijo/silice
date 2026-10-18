"""`/v1/produccion`: la arenera, cuánto hay y cuánto queda (Tarea 4.8; RF-134, RF-127 a RF-133).

Materiales, movimientos (producción, despacho y ajuste por conteo), existencias por fecha, la
importación de reportes de báscula `.csv`/`.xlsx` y la bandeja de pesajes sospechosos. Los servicios
son los de `produccion/`; esta capa solo traduce HTTP: texto a `Decimal` en la frontera, errores a
códigos y la transacción de cada petición.

Reglas de la frontera:

- **Cantidades como texto** (`str`) en la entrada y en la salida, nunca un número JSON; un texto que
  no es decimal es 422. Las rutas de `ajuste` reciben el **conteo físico** en `cantidad` y guardan
  la diferencia con la existencia teórica a esa fecha.
- **La API no usa el reloj** para decidir validez: `fecha_referencia` (para detectar fechas futuras
  en la báscula) es obligatoria y la manda el cliente; `ahora` al resolver o descartar también.
- **Cada petición es una transacción** (`SesionInstalacionDep`): lo que registra queda confirmado al
  terminar bien y un error, de cualquier tipo, no deja nada a medias.
- **Usuario de lo que se escribe**: `USUARIO_API` (RT-S4-4), pues la clave no entrega su identidad
  a la ruta.

Errores, siempre `{"detalle": ...}`: código o ticket repetido y pesaje sospechoso ya cerrado 409;
pesaje sospechoso inexistente 404; extensión que no es `.csv` ni `.xlsx` 415; cuerpo de más de
20 MiB 413 (el tope real lo pone `api.proteccion`; el archivo se lee además por bloques); dato
inválido, archivo rechazado por la guardia (`ArchivoRechazado`) o por el lector (`ReporteRechazado`)
422 con su mensaje, escrito para el usuario; `MapeoNecesario` 422 con el mensaje y la lista
`faltan`; cualquier otro fallo 500 con un mensaje fijo y el detalle solo en el registro del
servidor.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from adapters.hoja_empresa.guardia import ArchivoRechazado, verificar_archivo
from api.dependencias import USUARIO_API, SesionInstalacionDep
from api.proteccion import LIMITE_CUERPO
from produccion.conectores.bascula import ReporteRechazado, leer
from produccion.conectores.detector_columnas import MapeoNecesario
from produccion.importacion import descartar, importar, pendientes, resolver
from produccion.inventario import (
    Conflicto,
    ErrorDeInventario,
    crear_material,
    registrar_ajuste_por_conteo,
    registrar_despacho,
    registrar_entrada,
    tablero,
)
from produccion.modelo import Material, Movimiento, PesajeSospechoso

router = APIRouter(prefix="/v1/produccion", tags=["produccion"])

LOG = logging.getLogger(__name__)

__all__ = ["USUARIO_API", "router"]

EXTENSIONES = (".csv", ".xlsx")
TIPOS_DE_MOVIMIENTO = ("entrada", "despacho", "ajuste")
UNIDADES_DE_PESO = ("kg", "t")
BLOQUE = 1024 * 1024  # se lee de a 1 MiB: un archivo de más se corta sin leerlo entero
TOPE_BYTES = LIMITE_CUERPO  # el del cuerpo entero (api.proteccion): 20 MiB
MENSAJE_IMPORTACION = "El reporte de báscula no se pudo importar."
ERRORES_DEL_USUARIO = (ArchivoRechazado, ReporteRechazado, ErrorDeInventario)


# --- Esquemas ------------------------------------------------------------------------------------


class MaterialEntrada(BaseModel):
    codigo: str
    nombre: str
    unidad_venta: str  # "m3" o "t"
    existencia_minima: str  # decimal con punto, en la unidad de venta
    densidad_t_m3: str | None = None  # dato de la empresa; sin valor por defecto


class MaterialRespuesta(BaseModel):
    id: int
    codigo: str
    nombre: str
    unidad_venta: str
    densidad_t_m3: str | None
    existencia_minima: str
    activo: bool


class MovimientoEntrada(BaseModel):
    material_codigo: str
    tipo: str  # "entrada", "despacho" o "ajuste" (con el CONTEO FÍSICO en `cantidad`)
    fecha: str  # ISO, AAAA-MM-DD
    cantidad: str
    nota: str = ""


class MovimientoRespuesta(BaseModel):
    id: int
    material_codigo: str
    fecha: str
    tipo: str
    cantidad: str  # del ajuste: la diferencia con signo
    ticket: str | None
    placa: str
    cliente: str
    nota: str
    origen: str
    usuario: str
    registrado: str


class ExistenciaRespuesta(BaseModel):
    codigo: str
    nombre: str
    unidad_venta: str
    existencia: str
    minima: str
    queda_poco: bool
    negativa: bool


class ImportacionRespuesta(BaseModel):
    registrados: int
    ya_registrados: int
    a_la_bandeja: int
    huella: str


class SospechosoRespuesta(BaseModel):
    id: int
    huella_archivo: str
    fila: int
    ticket: str
    fecha_texto: str
    placa: str
    material_texto: str
    bruto_texto: str
    tara_texto: str
    neto_texto: str
    motivo: str
    estado: str


class ResolverEntrada(BaseModel):
    material_codigo: str
    fecha: str  # ISO, AAAA-MM-DD
    neto_t: str  # toneladas, decimal con punto
    ticket: str
    ahora: str  # fecha y hora ISO local, sin zona: la manda el cliente


class DescartarEntrada(BaseModel):
    ahora: str


# --- Frontera: texto a tipos ---------------------------------------------------------------------


def _decimal(texto: str, campo: str) -> Decimal:
    """`Decimal` exacto del texto; 422 si no es un decimal con punto. Un número JSON ni llega aquí
    (el esquema pide `str`)."""
    try:
        return Decimal(texto.strip())
    except InvalidOperation:
        raise HTTPException(
            422,
            f"'{campo}' debe ser un número decimal con punto (por ejemplo 12.5): «{texto[:40]}».",
        ) from None


def _fecha(texto: str, campo: str) -> date:
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        raise HTTPException(
            422, f"'{campo}' no es una fecha ISO válida (AAAA-MM-DD): «{texto[:40]}»."
        ) from None


def _instante(texto: str, campo: str) -> datetime:
    """Fecha y hora ISO local (`2026-10-18T09:30:00`). La base guarda la hora sin zona, así que una
    con zona se rechaza en vez de descartarle la zona en silencio."""
    try:
        valor = datetime.fromisoformat(texto.strip())
    except ValueError:
        valor = None
    if valor is None or valor.tzinfo is not None:
        raise HTTPException(
            422,
            f"'{campo}' debe ser fecha y hora ISO local, sin zona (AAAA-MM-DDThh:mm:ss): "
            f"«{texto[:40]}».",
        )
    return valor


def _material_por_codigo(sesion: Session, codigo: str) -> Material:
    material = sesion.scalar(select(Material).where(Material.codigo == codigo.strip()))
    if material is None:
        raise ErrorDeInventario(
            f"No existe un material con el código «{codigo.strip()[:40]}». "
            "Elija uno de la lista de materiales."
        )
    return material


@contextmanager
def _conflictos() -> Iterator[None]:
    """Un dato que choca con uno ya registrado es 409; el resto de `ErrorDeInventario` (un
    `ValueError`) lo vuelve 422 el manejador global de `api.main`."""
    try:
        yield
    except Conflicto as error:
        raise HTTPException(409, str(error)) from None


# --- Salida --------------------------------------------------------------------------------------


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _material_respuesta(material: Material) -> MaterialRespuesta:
    return MaterialRespuesta(
        id=material.id,
        codigo=material.codigo,
        nombre=material.nombre,
        unidad_venta=material.unidad_venta,
        densidad_t_m3=_texto(material.densidad_t_m3),
        existencia_minima=format(material.existencia_minima, "f"),
        activo=material.activo,
    )


def _movimiento_respuesta(movimiento: Movimiento, material_codigo: str) -> MovimientoRespuesta:
    return MovimientoRespuesta(
        id=movimiento.id,
        material_codigo=material_codigo,
        fecha=movimiento.fecha.isoformat(),
        tipo=movimiento.tipo,
        cantidad=format(movimiento.cantidad, "f"),
        ticket=movimiento.ticket,
        placa=movimiento.placa,
        cliente=movimiento.cliente,
        nota=movimiento.nota,
        origen=movimiento.origen,
        usuario=movimiento.usuario,
        registrado=movimiento.registrado.isoformat(),
    )


def _sospechoso_respuesta(s: PesajeSospechoso) -> SospechosoRespuesta:
    return SospechosoRespuesta(
        id=s.id,
        huella_archivo=s.huella_archivo,
        fila=s.fila,
        ticket=s.ticket,
        fecha_texto=s.fecha_texto,
        placa=s.placa,
        material_texto=s.material_texto,
        bruto_texto=s.bruto_texto,
        tara_texto=s.tara_texto,
        neto_texto=s.neto_texto,
        motivo=s.motivo,
        estado=s.estado,
    )


# --- Materiales ----------------------------------------------------------------------------------


@router.get("/materiales", response_model=list[MaterialRespuesta])
def listar_materiales(sesion: SesionInstalacionDep) -> list[MaterialRespuesta]:
    """Los materiales de la arenera, por código."""
    materiales = sesion.scalars(select(Material).order_by(Material.codigo))
    return [_material_respuesta(m) for m in materiales]


@router.post("/materiales", response_model=MaterialRespuesta, status_code=201)
def crear_un_material(entrada: MaterialEntrada, sesion: SesionInstalacionDep) -> MaterialRespuesta:
    """Da de alta un material. La densidad es dato de la empresa (sin valor por defecto). Código
    repetido: 409; datos inválidos: 422."""
    minima = _decimal(entrada.existencia_minima, "existencia_minima")
    densidad = (
        None if entrada.densidad_t_m3 is None else _decimal(entrada.densidad_t_m3, "densidad_t_m3")
    )
    with _conflictos():
        material = crear_material(
            sesion,
            codigo=entrada.codigo,
            nombre=entrada.nombre,
            unidad_venta=entrada.unidad_venta,
            existencia_minima=minima,
            densidad_t_m3=densidad,
        )
    return _material_respuesta(material)


# --- Movimientos y existencias -------------------------------------------------------------------


@router.post(
    "/movimientos",
    response_model=MovimientoRespuesta | None,
    status_code=201,
    responses={
        200: {
            "description": "Ajuste sin diferencia: el conteo coincide con la existencia (`null`)."
        }
    },
)
def registrar_un_movimiento(
    entrada: MovimientoEntrada, sesion: SesionInstalacionDep
) -> MovimientoRespuesta | JSONResponse:
    """Registra una entrada (producción), un despacho o un ajuste por conteo. En el ajuste,
    `cantidad` es el **conteo físico** y se guarda la diferencia con la existencia a esa fecha; si
    no hay diferencia responde 200 con `null`. Un despacho nunca se bloquea por dejar la
    existencia negativa (RT-S4-2)."""
    if entrada.tipo not in TIPOS_DE_MOVIMIENTO:
        raise HTTPException(422, "'tipo' debe ser entrada, despacho o ajuste.")
    fecha = _fecha(entrada.fecha, "fecha")
    cantidad = _decimal(entrada.cantidad, "cantidad")
    material = _material_por_codigo(sesion, entrada.material_codigo)
    nota = entrada.nota.strip()
    with _conflictos():
        if entrada.tipo == "entrada":
            movimiento = registrar_entrada(
                sesion, material.id, fecha, cantidad, usuario=USUARIO_API, nota=nota
            )
        elif entrada.tipo == "despacho":
            movimiento = registrar_despacho(
                sesion, material.id, fecha, cantidad, usuario=USUARIO_API, nota=nota
            )
        else:
            movimiento = registrar_ajuste_por_conteo(
                sesion, material.id, fecha, cantidad, usuario=USUARIO_API, nota=nota
            )
    if movimiento is None:
        return JSONResponse(content=None, status_code=200)
    return _movimiento_respuesta(movimiento, material.codigo)


@router.get("/existencias", response_model=list[ExistenciaRespuesta])
def ver_existencias(
    sesion: SesionInstalacionDep,
    a_fecha: Annotated[
        str | None,
        Query(description="Existencia a esa fecha, ISO; sin ella, la de hoy en adelante"),
    ] = None,
) -> list[ExistenciaRespuesta]:
    """El tablero «cuánto hay y cuánto queda» de los materiales activos, por código."""
    hasta = None if a_fecha is None or not a_fecha.strip() else _fecha(a_fecha, "a_fecha")
    return [
        ExistenciaRespuesta(
            codigo=fila.material.codigo,
            nombre=fila.material.nombre,
            unidad_venta=fila.material.unidad_venta,
            existencia=format(fila.existencia, "f"),
            minima=format(fila.minima, "f"),
            queda_poco=fila.queda_poco,
            negativa=fila.negativa,
        )
        for fila in tablero(sesion, hasta)
    ]


# --- Importar el reporte de báscula --------------------------------------------------------------


def _nombre(archivo: UploadFile) -> str:
    """Solo el último componente del nombre que manda el cliente (sin rutas)."""
    return (archivo.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()


def _extension(nombre: str) -> str:
    minuscula = nombre.lower()
    for extension in EXTENSIONES:
        if minuscula.endswith(extension) and len(nombre) > len(extension):
            return extension
    recibido = nombre[:120] or "sin nombre"
    raise HTTPException(
        415, f"El reporte debe ser un archivo .csv o .xlsx (se recibió «{recibido}»)."
    )


async def _leer_archivo(archivo: UploadFile) -> bytes:
    """Los bytes de la subida, por bloques; 413 en cuanto pasan de `TOPE_BYTES`."""
    excedido = HTTPException(
        413,
        f"El reporte supera el máximo de {TOPE_BYTES // 2**20} MiB. Divídalo en reportes menores.",
    )
    if archivo.size is not None and archivo.size > TOPE_BYTES:
        raise excedido
    partes: list[bytes] = []
    total = 0
    while bloque := await archivo.read(BLOQUE):
        total += len(bloque)
        if total > TOPE_BYTES:
            raise excedido
        partes.append(bloque)
    return b"".join(partes)


def _unidad_de_peso(texto: str | None) -> str | None:
    if texto is None or not texto.strip():
        return None
    unidad = texto.strip().lower()
    if unidad not in UNIDADES_DE_PESO:
        raise HTTPException(422, f"'unidad_peso' debe ser kg o t: «{texto[:20]}».")
    return unidad


def _mapeo(texto: str | None) -> dict[str, int] | None:
    """`{"campo": índice}` desde el JSON del formulario; 422 si no es esa forma."""
    if texto is None or not texto.strip():
        return None
    try:
        valor = json.loads(texto)
    except ValueError:
        valor = None
    forma_valida = isinstance(valor, dict) and all(
        isinstance(campo, str) and isinstance(i, int) and not isinstance(i, bool)
        for campo, i in valor.items()
    )
    if not forma_valida:
        raise HTTPException(
            422,
            "El 'mapeo' debe ser un JSON {\"campo\": número de columna}, con la primera "
            'columna en 0 (por ejemplo {"material": 4}).',
        )
    return valor


@router.post(
    "/bascula/importar",
    response_model=ImportacionRespuesta,
    responses={
        413: {"description": "El cuerpo pasa de 20 MiB."},
        415: {"description": "La extensión no es .csv ni .xlsx."},
        422: {"description": "Archivo rechazado, unidad ausente o mapeo necesario (`faltan`)."},
    },
)
async def importar_reporte(
    sesion: SesionInstalacionDep,
    archivo: Annotated[UploadFile, File(description="Reporte de la báscula (.csv o .xlsx)")],
    fecha_referencia: Annotated[
        str, Form(description="«Hoy» para detectar fechas futuras, ISO (AAAA-MM-DD). Obligatoria.")
    ],
    unidad_peso: Annotated[
        str | None, Form(description="kg o t, si el encabezado del peso no la trae")
    ] = None,
    mapeo: Annotated[
        str | None, Form(description='JSON {"campo": índice de columna (desde 0)}, opcional')
    ] = None,
) -> ImportacionRespuesta | JSONResponse:
    """Importa un reporte de báscula: lo leído y coherente son despachos; lo dudoso va a la bandeja
    de pesajes sospechosos. Idempotente: reimportar el mismo reporte no duplica nada. Sin unidad
    del peso (ni en el encabezado ni en `unidad_peso`) no se importa nada."""
    nombre = _nombre(archivo)
    extension = _extension(nombre)
    referencia = _fecha(fecha_referencia, "fecha_referencia")
    unidad = _unidad_de_peso(unidad_peso)
    mapa = _mapeo(mapeo)
    datos = await _leer_archivo(archivo)
    try:
        if extension == ".xlsx":
            await run_in_threadpool(verificar_archivo, datos, nombre)
        lectura = await run_in_threadpool(
            lambda: leer(datos, nombre, fecha_referencia=referencia, unidad_peso=unidad, mapeo=mapa)
        )
        resultado = await run_in_threadpool(lambda: importar(sesion, lectura, usuario=USUARIO_API))
    except HTTPException:
        raise
    except MapeoNecesario as error:
        return JSONResponse(
            status_code=422, content={"detalle": str(error), "faltan": list(error.faltan)}
        )
    except Conflicto as error:
        raise HTTPException(409, str(error)) from None
    except ERRORES_DEL_USUARIO as error:
        raise HTTPException(422, str(error)) from None
    except Exception as error:  # noqa: BLE001 - frontera: nunca una traza al cliente
        LOG.error(
            "POST /v1/produccion/bascula/importar: fallo inesperado (%s)",
            type(error).__name__,
            exc_info=error,
        )
        raise HTTPException(500, MENSAJE_IMPORTACION) from None
    return ImportacionRespuesta(
        registrados=resultado.registrados,
        ya_registrados=resultado.ya_registrados,
        a_la_bandeja=resultado.a_la_bandeja,
        huella=resultado.huella,
    )


# --- Bandeja de pesajes sospechosos --------------------------------------------------------------


@router.get("/pesajes-sospechosos", response_model=list[SospechosoRespuesta])
def listar_sospechosos(sesion: SesionInstalacionDep) -> list[SospechosoRespuesta]:
    """Los pesajes sospechosos pendientes, en el orden en que llegaron."""
    return [_sospechoso_respuesta(s) for s in pendientes(sesion)]


def _sospechoso_pendiente(sesion: Session, id_sospechoso: int) -> None:
    """404 si no existe y 409 si ya se resolvió o descartó."""
    sospechoso = sesion.get(PesajeSospechoso, id_sospechoso)
    if sospechoso is None:
        raise HTTPException(404, "No existe ese pesaje sospechoso. Actualice la bandeja.")
    if sospechoso.estado != "pendiente":
        raise HTTPException(409, "Ese pesaje sospechoso ya fue resuelto o descartado.")


@router.post(
    "/pesajes-sospechosos/{id_sospechoso}/resolver",
    response_model=MovimientoRespuesta,
    status_code=201,
)
def resolver_sospechoso(
    id_sospechoso: int, entrada: ResolverEntrada, sesion: SesionInstalacionDep
) -> MovimientoRespuesta:
    """Crea el despacho con los valores corregidos y cierra el sospechoso como resuelto. Ya cerrado
    o ticket ya registrado: 409; inexistente: 404."""
    fecha = _fecha(entrada.fecha, "fecha")
    neto = _decimal(entrada.neto_t, "neto_t")
    ahora = _instante(entrada.ahora, "ahora")
    _sospechoso_pendiente(sesion, id_sospechoso)
    with _conflictos():
        movimiento = resolver(
            sesion,
            id_sospechoso,
            material_codigo=entrada.material_codigo,
            fecha=fecha,
            neto_t=neto,
            ticket=entrada.ticket,
            usuario=USUARIO_API,
            ahora=ahora,
        )
    material = sesion.get(Material, movimiento.material_id)
    return _movimiento_respuesta(movimiento, material.codigo if material else "")


@router.post("/pesajes-sospechosos/{id_sospechoso}/descartar", status_code=204)
def descartar_sospechoso(
    id_sospechoso: int, entrada: DescartarEntrada, sesion: SesionInstalacionDep
) -> Response:
    """Cierra el sospechoso como descartado, sin crear ningún despacho. Ya cerrado: 409."""
    ahora = _instante(entrada.ahora, "ahora")
    _sospechoso_pendiente(sesion, id_sospechoso)
    descartar(sesion, id_sospechoso, usuario=USUARIO_API, ahora=ahora)
    return Response(status_code=204)
