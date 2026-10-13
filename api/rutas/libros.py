"""`/v1/libros`: auditar y devolver calcado el libro de presupuesto de la empresa (spec 1.5 §5).

Dos rutas con la misma entrada multipart:

- `libro` (obligatorio): el `.xlsx` de la empresa.
- `pdf` (opcional): el PDF que se entregó (L10 si es un documento simple, L11 si es el impreso).
- `anterior` (opcional): otra versión del mismo libro, para las alertas de cambio de precio (§4).
- `fecha_libro` (opcional, ISO): sin ella, la de la PORTADA (F-D8).
- `fecha_devolucion` (**obligatoria**, ISO): la API nunca usa el reloj para auditar; la misma
  petición da siempre la misma respuesta (como `POST /v1/auditorias`).

`POST /v1/libros/auditoria` responde el informe en JSON; `POST /v1/libros/devolucion`, el libro
calcado (`.xlsx`). Todo ocurre **en memoria** (F-D9): ningún archivo toca el disco y nada se
guarda en la base. Los montos viajan como texto.

Errores: extensión equivocada 415; un archivo de más de 25 MB 413 (se lee por bloques y se corta
al pasar el tope); fecha mal escrita 422; archivo rechazado por la guardia o el lector
(`ArchivoRechazado`, F-D10) 422 con su mensaje, escrito para el usuario. La clave de API, el tope
de 20 MiB del cuerpo entero y los hosts permitidos los pone `api.proteccion` para toda la
aplicación (`CON_CLAVE` en `api.main`).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from adapters.hoja_empresa.guardia import MAX_BYTES, ArchivoRechazado
from api.dependencias import SesionDep
from fusion.alertas import ContextoPrecios
from fusion.proceso import ResultadoFusion, devolver, procesar_libro, servicios_desde_sesion

router = APIRouter(prefix="/v1/libros", tags=["libros"])

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
BLOQUE = 1024 * 1024  # se lee de a 1 MiB: un archivo de más se corta sin leerlo entero


# --- Esquemas de la respuesta --------------------------------------------------------------------


class LibroOrigenRespuesta(BaseModel):
    nombre: str
    sha256: str


class HallazgoLibroRespuesta(BaseModel):
    codigo: str
    severidad: str
    descripcion: str
    celda: str
    impacto: str | None = None
    accion: str


class AlertaPrecioRespuesta(BaseModel):
    codigo: str
    descripcion: str
    tipo: str
    moneda: str
    precio: str
    fecha: str
    fuente: str
    tasa: str | None = None
    precio_bs: str | None = None
    variacion: str | None = None
    mensaje: str


class TrazaRespuesta(BaseModel):
    dato: str
    valor: str
    origen: str
    nota: str = ""


class LibroAuditadoRespuesta(BaseModel):
    libro: LibroOrigenRespuesta
    fecha_libro: str | None
    fecha_devolucion: str | None
    cumple: bool
    por_severidad: dict[str, int]
    totales_libro: dict[str, str]
    totales_silice: dict[str, str]
    hallazgos: list[HallazgoLibroRespuesta]
    alertas: list[AlertaPrecioRespuesta]
    trazabilidad: list[TrazaRespuesta]
    metadatos: dict[str, str]


# --- Entrada -------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Entrada:
    libro: bytes
    nombre: str
    pdf: bytes | None
    pdf_nombre: str
    anterior: bytes | None
    anterior_nombre: str
    fecha_libro: date | None
    fecha_devolucion: date


def _nombre(archivo: UploadFile) -> str:
    """Solo el último componente del nombre que manda el cliente (sin rutas)."""
    return (archivo.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()


def _exigir_extension(nombre: str, extension: str, campo: str) -> None:
    if not nombre.lower().endswith(extension) or len(nombre) <= len(extension):
        recibido = nombre[:120] or "sin nombre"
        mensaje = f"'{campo}' debe ser un archivo {extension} (se recibió «{recibido}»)."
        if extension == ".xlsx":
            mensaje += " Solo se aceptan libros de Excel .xlsx sin macros."
        raise HTTPException(415, mensaje)


async def _leer(archivo: UploadFile, campo: str) -> bytes:
    """Los bytes de la subida, por bloques; 413 en cuanto pasan de `MAX_BYTES` (25 MB, F-D10)."""
    excedido = HTTPException(
        413, f"'{campo}' supera el máximo de {MAX_BYTES // 2**20} MB por archivo."
    )
    if archivo.size is not None and archivo.size > MAX_BYTES:
        raise excedido
    partes: list[bytes] = []
    total = 0
    while bloque := await archivo.read(BLOQUE):
        total += len(bloque)
        if total > MAX_BYTES:
            raise excedido
        partes.append(bloque)
    return b"".join(partes)


def _fecha(texto: str | None, campo: str) -> date | None:
    if texto is None or not texto.strip():
        return None
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        raise HTTPException(
            422, f"'{campo}' no es una fecha ISO válida (AAAA-MM-DD): «{texto[:40]}»."
        ) from None


def _presente(archivo: UploadFile | None) -> bool:
    """Un campo de archivo opcional que el navegador manda vacío cuenta como ausente."""
    return archivo is not None and bool(archivo.filename)


async def entrada_del_libro(
    libro: Annotated[UploadFile, File(description="Libro de la empresa (.xlsx sin macros)")],
    fecha_devolucion: Annotated[
        str, Form(description="Fecha de devolución, ISO (AAAA-MM-DD). Obligatoria.")
    ],
    pdf: Annotated[UploadFile | None, File(description="PDF entregado (opcional)")] = None,
    anterior: Annotated[
        UploadFile | None, File(description="Otra versión del libro (.xlsx, opcional)")
    ] = None,
    fecha_libro: Annotated[
        str | None, Form(description="Fecha del libro, ISO; sin ella, la de la PORTADA")
    ] = None,
) -> _Entrada:
    """Valida y lee la petición multipart: extensiones (415), tamaños (413) y fechas (422)."""
    nombre = _nombre(libro)
    _exigir_extension(nombre, ".xlsx", "libro")
    hay_pdf = _presente(pdf)
    hay_anterior = _presente(anterior)
    if hay_pdf:
        _exigir_extension(_nombre(pdf), ".pdf", "pdf")
    if hay_anterior:
        _exigir_extension(_nombre(anterior), ".xlsx", "anterior")
    devolucion = _fecha(fecha_devolucion, "fecha_devolucion")
    if devolucion is None:
        raise HTTPException(422, "falta 'fecha_devolucion' (ISO, AAAA-MM-DD).")
    fecha = _fecha(fecha_libro, "fecha_libro")
    return _Entrada(
        libro=await _leer(libro, "libro"),
        nombre=nombre,
        pdf=await _leer(pdf, "pdf") if hay_pdf else None,
        pdf_nombre=_nombre(pdf) if hay_pdf else "",
        anterior=await _leer(anterior, "anterior") if hay_anterior else None,
        anterior_nombre=_nombre(anterior) if hay_anterior else "",
        fecha_libro=fecha,
        fecha_devolucion=devolucion,
    )


def contexto_de_la_api(sesion: SesionDep) -> ContextoPrecios:
    """Tasas del BCV y precios propios de ESTA instalación (F-D8). Las pruebas sustituyen esta
    dependencia."""
    return servicios_desde_sesion(sesion)


EntradaDep = Annotated[_Entrada, Depends(entrada_del_libro)]
ContextoDep = Annotated[ContextoPrecios, Depends(contexto_de_la_api)]


async def _procesar(entrada: _Entrada, contexto: ContextoPrecios) -> ResultadoFusion:
    try:
        return await run_in_threadpool(
            lambda: procesar_libro(
                entrada.libro,
                entrada.nombre,
                pdf=entrada.pdf,
                pdf_nombre=entrada.pdf_nombre,
                contexto=contexto,
                fecha_libro=entrada.fecha_libro,
                fecha_devolucion=entrada.fecha_devolucion,
                otro=entrada.anterior,
                **({"otro_nombre": entrada.anterior_nombre} if entrada.anterior else {}),
            )
        )
    except ArchivoRechazado as error:
        raise HTTPException(422, str(error)) from None


# --- Serialización -------------------------------------------------------------------------------


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _iso(valor: date | None) -> str | None:
    return None if valor is None else valor.isoformat()


def _montos(mapa) -> dict[str, str]:
    return {str(k): format(v, "f") for k, v in (mapa or {}).items() if v is not None}


def _nombre_de_descarga(original: str) -> str:
    """`<nombre>-silice.xlsx` con solo [A-Za-z0-9 ._-]: sin rutas, comillas ni saltos de línea
    que rompan la cabecera `Content-Disposition`."""
    base = original[: -len(".xlsx")] if original.lower().endswith(".xlsx") else original
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9 ._-]", "_", base).strip(" .")[:120] or "libro"
    return f"{base}-silice.xlsx"


# --- Rutas ---------------------------------------------------------------------------------------


@router.post("/auditoria", response_model=LibroAuditadoRespuesta)
async def auditar_libro(entrada: EntradaDep, contexto: ContextoDep) -> LibroAuditadoRespuesta:
    """Audita el libro y responde el informe (hallazgos, alertas y trazabilidad). No guarda
    nada."""
    r = await _procesar(entrada, contexto)
    return LibroAuditadoRespuesta(
        libro=LibroOrigenRespuesta(nombre=r.libro.nombre, sha256=r.libro.sha256),
        fecha_libro=_iso(r.fecha_libro),
        fecha_devolucion=_iso(r.fecha_devolucion),
        cumple=r.informe.cumple,
        por_severidad={s.name: n for s, n in r.informe.por_severidad().items()},
        totales_libro=_montos(r.libro.totales),
        totales_silice=_montos(r.totales_silice),
        hallazgos=[
            HallazgoLibroRespuesta(
                codigo=h.codigo,
                severidad=h.severidad,
                descripcion=h.descripcion,
                celda=h.celda,
                impacto=_texto(h.impacto),
                accion=h.accion,
            )
            for h in r.hallazgos_tabla
        ],
        alertas=[
            AlertaPrecioRespuesta(
                codigo=a.codigo,
                descripcion=a.descripcion,
                tipo=a.tipo,
                moneda=a.moneda,
                precio=format(a.precio, "f"),
                fecha=a.fecha,
                fuente=a.fuente,
                tasa=_texto(a.tasa),
                precio_bs=_texto(a.precio_bs),
                variacion=_texto(a.variacion),
                mensaje=a.mensaje,
            )
            for a in r.alertas
        ],
        trazabilidad=[
            TrazaRespuesta(dato=t.dato, valor=t.valor, origen=t.origen, nota=t.nota)
            for t in r.trazabilidad
        ],
        metadatos={str(k): str(v) for k, v in (r.metadatos or {}).items()},
    )


@router.post(
    "/devolucion",
    response_class=Response,
    responses={200: {"content": {TIPO_XLSX: {}}, "description": "El libro calcado (.xlsx)."}},
)
async def devolver_libro(entrada: EntradaDep, contexto: ContextoDep) -> Response:
    """Devuelve el libro calcado: mismas hojas, valores de Silice y las hojas AUDITORÍA,
    TRAZABILIDAD y ALERTAS USD-Bs (spec 1.5 §1). No guarda nada."""
    r = await _procesar(entrada, contexto)
    try:
        contenido = await run_in_threadpool(devolver, r)
    except ArchivoRechazado as error:
        raise HTTPException(422, str(error)) from None
    return Response(
        content=contenido,
        media_type=TIPO_XLSX,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_nombre_de_descarga(entrada.nombre)}"'
            ),
            "X-Silice-Sha256-Origen": r.libro.sha256,
        },
    )
