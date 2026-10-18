"""`/v1/libros`: auditar y devolver calcado el libro de presupuesto de la empresa, revisar solo
el PDF simple de un presupuesto (spec 1.5 §5, UC-25) o replicar el aspecto del libro para el visor
de la interfaz nueva (Sílice 1.2.0, RF-111, UC-26).

Dos rutas con la misma entrada multipart:

- `libro` (obligatorio): el `.xlsx` de la empresa.
- `pdf` (opcional): el PDF que se entregó. Si trae el bloque de totales del libro impreso, se
  cotejan su subtotal, IVA y total con los del libro (L11); si es un PDF simple (tablas de
  cómputos o de presupuesto), se revisa consigo mismo (L10). Un PDF simple **sin** libro va por
  `POST /v1/libros/pdf`.
- `anterior` (opcional): otra versión del mismo libro, para las alertas de cambio de precio (§4).
- `fecha_libro` (opcional, ISO): sin ella, la de la PORTADA (F-D8).
- `fecha_devolucion` (**obligatoria**, ISO): la API nunca usa el reloj para auditar; la misma
  petición da siempre la misma respuesta (como `POST /v1/auditorias`).
- `umbral` (opcional, decimal con punto, 0 < umbral < 1): la variación de precio desde la que hay
  alerta, como fracción (`0.05` = 5 %, el valor por omisión).

`POST /v1/libros/auditoria` responde el informe en JSON, con los `indicadores` del libro frente
a Sílice (RS2-7, RF-116; `indicadores_de`); `POST /v1/libros/devolucion`, el libro calcado
(`.xlsx`). `POST /v1/libros/pdf` recibe solo `pdf` (el presupuesto impreso, formato 001/002, sin
Excel) y responde en JSON los hallazgos L10 del PDF cotejado consigo mismo. `POST
/v1/libros/replica` recibe solo `libro` y responde su réplica visual (`LibroVisualRespuesta`,
espejo del contrato neutro `adapters.hoja_empresa.visual.LibroVisual`, RS2-1). Todo ocurre **en
memoria** (F-D9): ningún archivo toca el disco y nada se guarda en la base. Los montos viajan como
texto.

Errores: extensión equivocada 415; un cuerpo de más de 20 MiB 413 (el tope real lo pone
`api.proteccion` al cuerpo entero de la petición, sin leerlo; cada archivo se lee además por
bloques y se corta al pasar ese mismo tope); fecha o umbral mal escritos 422; archivo rechazado por
la guardia (`ArchivoRechazado`, F-D10) o libro que no se puede interpretar (`LibroNoInterpretable`)
422 con su mensaje, escrito para el usuario (también el libro demasiado grande para el visor,
`LibroDemasiadoGrande`, que es un `ArchivoRechazado`); cualquier otro fallo al procesar 500 con un
mensaje fijo y el detalle solo en el registro del servidor (`logging`), nunca en la respuesta. El
tope del cuerpo y los hosts permitidos los pone `api.proteccion` para toda la aplicación; el acceso
lo exige `api.main` con `exigir_clave_o_sesion(Accion.LEER_PROYECTO)` (RS2-5): con la cabecera
`X-Silice-Clave`, como antes; sin ella, la cookie de sesión del navegador con CSRF y un rol que
arma o revisa.

`indicadores_de` vive aquí y no en `fusion/`: es aritmética de **presentación** sobre los totales
que `fusion.proceso` ya calculó (una resta y un porcentaje en centésimas; NORMAS §2.3: «se
redondea a dos decimales únicamente al presentar»), con los títulos y el sentido IBCS que solo usa
la interfaz. No decide nada de la auditoría.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from adapters.hoja_empresa.guardia import MAX_BYTES, ArchivoRechazado
from adapters.hoja_empresa.modelo import LibroNoInterpretable
from adapters.hoja_empresa.visual import LibroVisual, replicar_libro
from api.dependencias import SesionDep
from api.proteccion import LIMITE_CUERPO
from fusion.alertas import ContextoPrecios
from fusion.proceso import (
    ResultadoFusion,
    auditar_pdf_simple,
    devolver,
    procesar_libro,
    servicios_desde_sesion,
)

router = APIRouter(prefix="/v1/libros", tags=["libros"])

LOG = logging.getLogger(__name__)

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
BLOQUE = 1024 * 1024  # se lee de a 1 MiB: un archivo de más se corta sin leerlo entero
# El tope real: el middleware corta el cuerpo entero (todos los archivos juntos) en 20 MiB antes de
# que la ruta lo vea, así que el de la guardia (`MAX_BYTES`, 25 MiB por archivo, F-D10) no se
# alcanza por la API.
TOPE_BYTES = min(MAX_BYTES, LIMITE_CUERPO)
UMBRAL_POR_OMISION = Decimal("0.05")
ERRORES_DEL_USUARIO = (ArchivoRechazado, LibroNoInterpretable)  # su mensaje es para el usuario
MENSAJE_LIBRO = "El libro no se pudo interpretar."
MENSAJE_PDF = "El PDF no se pudo interpretar."
#: Indicadores de la franja (RS2-7): clave del total -> título, en el orden en que se muestran.
INDICADORES = {"SUBSINIVA": "Subtotal sin IVA", "IVATOT": "IVA", "TOTALGEN": "Total general"}
CENTESIMA = Decimal("0.01")


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


class IndicadorRespuesta(BaseModel):
    """Un total del libro (`actual`) frente al de Sílice (`meta`), RS2-7: `delta = actual - meta`;
    `delta_pct` en centésimas (redondeo al par), nulo si la meta es cero. `sentido = "costo"`: que
    el libro declare más de lo que calcula Sílice es desfavorable (IBCS)."""

    clave: str
    titulo: str
    actual: str
    meta: str
    delta: str
    delta_pct: str | None
    sentido: Literal["costo"]


class LibroAuditadoRespuesta(BaseModel):
    libro: LibroOrigenRespuesta
    fecha_libro: str | None
    fecha_devolucion: str | None
    cumple: bool
    por_severidad: dict[str, int]
    totales_libro: dict[str, str]
    totales_silice: dict[str, str]
    indicadores: list[IndicadorRespuesta]
    hallazgos: list[HallazgoLibroRespuesta]
    alertas: list[AlertaPrecioRespuesta]
    trazabilidad: list[TrazaRespuesta]
    metadatos: dict[str, str]


class PdfOrigenRespuesta(BaseModel):
    nombre: str
    sha256: str
    numero: str
    fecha: str


class PdfSimpleRespuesta(BaseModel):
    pdf: PdfOrigenRespuesta
    cumple: bool
    por_severidad: dict[str, int]
    renglones_computos: int
    renglones_presupuesto: int
    total_computos: str | None
    total_impreso: str | None
    notas: list[str]
    hallazgos: list[HallazgoLibroRespuesta]


class EstiloVisualRespuesta(BaseModel):
    """Espejo de `visual.EstiloVisual`; `bordes`: arriba, derecha, abajo, izquierda."""

    relleno: str | None
    fuente: str | None
    tamano: str | None
    negrita: bool
    cursiva: bool
    subrayado: bool
    color: str | None
    alineacion_h: str | None
    alineacion_v: str | None
    ajustar_texto: bool
    formato_numero: str
    bordes: tuple[str | None, str | None, str | None, str | None]


class CeldaVisualRespuesta(BaseModel):
    """Espejo de `visual.CeldaVisual`: `fila` y `columna` base 1, `ref` sin `$`."""

    ref: str
    fila: int
    columna: int
    mostrado: str
    formula: str | None
    estilo: int


class HojaVisualRespuesta(BaseModel):
    """Espejo de `visual.HojaVisual`. En `anchos` y `altos` la columna o la fila (base 1) va como
    texto: las claves de un objeto JSON son texto."""

    nombre: str
    visible: bool
    filas: int
    columnas: int
    anchos: dict[str, str]
    altos: dict[str, str]
    ocultas_filas: list[int]
    ocultas_columnas: list[int]
    combinadas: list[str]
    fijas: str | None
    celdas: list[CeldaVisualRespuesta]


class LibroVisualRespuesta(BaseModel):
    """Réplica visual del libro (RF-111): espejo del contrato neutro `visual.LibroVisual`."""

    nombre: str
    sha256: str
    hojas: list[HojaVisualRespuesta]
    estilos: list[EstiloVisualRespuesta]


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
    umbral: Decimal = UMBRAL_POR_OMISION


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
    """Los bytes de la subida, por bloques; 413 en cuanto pasan de `TOPE_BYTES` (20 MiB: el tope
    del cuerpo entero que pone `api.proteccion`, más estricto que los 25 MiB de la guardia)."""
    excedido = HTTPException(
        413,
        f"'{campo}' supera el máximo de {TOPE_BYTES / 2**20:g} MiB (el tope de la petición "
        "entera, con todos sus archivos).",
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


def _fecha(texto: str | None, campo: str) -> date | None:
    if texto is None or not texto.strip():
        return None
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        raise HTTPException(
            422, f"'{campo}' no es una fecha ISO válida (AAAA-MM-DD): «{texto[:40]}»."
        ) from None


def _umbral(texto: str | None) -> Decimal:
    """La fracción de alerta (0 < u < 1); sin ella, 0.05. 422 si no es un decimal en ese rango."""
    if texto is None or not texto.strip():
        return UMBRAL_POR_OMISION
    try:
        valor = Decimal(texto.strip())
    except InvalidOperation:
        valor = None
    if valor is None or not valor.is_finite() or not Decimal(0) < valor < Decimal(1):
        raise HTTPException(
            422,
            f"'umbral' debe ser un decimal con punto mayor que 0 y menor que 1 (0.05 = 5 %): "
            f"«{texto[:40]}».",
        )
    return valor


def _presente(archivo: UploadFile | None) -> bool:
    """Un campo de archivo opcional que el navegador manda vacío cuenta como ausente."""
    return archivo is not None and bool(archivo.filename)


async def entrada_del_libro(
    libro: Annotated[UploadFile, File(description="Libro de la empresa (.xlsx sin macros)")],
    fecha_devolucion: Annotated[
        str, Form(description="Fecha de devolución, ISO (AAAA-MM-DD). Obligatoria.")
    ],
    pdf: Annotated[
        UploadFile | None, File(description="PDF entregado (opcional; L11 o L10)")
    ] = None,
    anterior: Annotated[
        UploadFile | None, File(description="Otra versión del libro (.xlsx, opcional)")
    ] = None,
    fecha_libro: Annotated[
        str | None, Form(description="Fecha del libro, ISO; sin ella, la de la PORTADA")
    ] = None,
    umbral: Annotated[
        str | None,
        Form(description="Variación de precio desde la que hay alerta, 0 < umbral < 1 (0.05)"),
    ] = None,
) -> _Entrada:
    """Valida y lee la petición multipart: extensiones (415), tamaños (413), fechas y umbral
    (422)."""
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
    fraccion = _umbral(umbral)
    return _Entrada(
        libro=await _leer(libro, "libro"),
        nombre=nombre,
        pdf=await _leer(pdf, "pdf") if hay_pdf else None,
        pdf_nombre=_nombre(pdf) if hay_pdf else "",
        anterior=await _leer(anterior, "anterior") if hay_anterior else None,
        anterior_nombre=_nombre(anterior) if hay_anterior else "",
        fecha_libro=fecha,
        fecha_devolucion=devolucion,
        umbral=fraccion,
    )


EntradaDep = Annotated[_Entrada, Depends(entrada_del_libro)]


def contexto_de_la_api(sesion: SesionDep, entrada: EntradaDep) -> ContextoPrecios:
    """Tasas del BCV y precios propios de ESTA instalación (F-D8), con el umbral de la petición.
    FastAPI resuelve `entrada` una sola vez por petición. Las pruebas sustituyen esta
    dependencia."""
    return servicios_desde_sesion(sesion, umbral=entrada.umbral)


ContextoDep = Annotated[ContextoPrecios, Depends(contexto_de_la_api)]


def _rechazo(error: Exception, mensaje_fijo: str, que: str) -> HTTPException:
    """Frontera: un error del usuario es 422 con su mensaje tal cual; cualquier otro es un fallo
    del servidor, 500 con un mensaje fijo, y el detalle (con la traza) solo al registro.

    Revisión de calidad V5: responder 422 a un defecto propio lo hacía pasar por error del cliente.
    """
    if isinstance(error, ERRORES_DEL_USUARIO):
        return HTTPException(422, str(error))
    LOG.error("%s: fallo inesperado (%s)", que, type(error).__name__, exc_info=error)
    return HTTPException(500, mensaje_fijo)


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
    except Exception as error:  # noqa: BLE001 - frontera: nunca un 500 ni una traza al cliente
        raise _rechazo(error, MENSAJE_LIBRO, "POST /v1/libros") from None


# --- Serialización -------------------------------------------------------------------------------


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _iso(valor: date | None) -> str | None:
    return None if valor is None else valor.isoformat()


def _montos(mapa) -> dict[str, str]:
    return {str(k): format(v, "f") for k, v in (mapa or {}).items() if v is not None}


def _exacto(valor: Decimal) -> str:
    """Texto decimal exacto sin ceros de relleno ni notación científica: `4358.2082500` ->
    `4358.20825`, `1E+3` -> `1000`, `-0.000` -> `0`. No redondea: solo quita lo que no es cifra."""
    texto = format(valor, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return "0" if texto in ("-0", "") else texto


def indicadores_de(
    totales_libro: Mapping[str, Decimal | None], totales_silice: Mapping[str, Decimal | None]
) -> list[IndicadorRespuesta]:
    """Los indicadores de la franja (RS2-7), en el orden de `INDICADORES` y solo con las claves
    presentes (y no nulas) en los dos totales: `actual` = libro, `meta` = Sílice,
    `delta = actual - meta` y `delta_pct = delta / meta * 100` en centésimas con redondeo al par,
    o `None` si `meta == 0`. Función pura; los montos salen como texto decimal exacto sin ceros de
    relleno (`_exacto`)."""
    indicadores: list[IndicadorRespuesta] = []
    for clave, titulo in INDICADORES.items():
        actual, meta = totales_libro.get(clave), totales_silice.get(clave)
        if actual is None or meta is None:
            continue
        delta = actual - meta
        pct = None if meta == 0 else (delta / meta * 100).quantize(CENTESIMA, ROUND_HALF_EVEN)
        indicadores.append(
            IndicadorRespuesta(
                clave=clave,
                titulo=titulo,
                actual=_exacto(actual),
                meta=_exacto(meta),
                delta=_exacto(delta),
                delta_pct=_texto(pct),
                sentido="costo",
            )
        )
    return indicadores


def _visual(libro: LibroVisual) -> LibroVisualRespuesta:
    """`LibroVisual` -> su espejo Pydantic; las claves int de `anchos` y `altos` pasan a texto."""
    return LibroVisualRespuesta(
        nombre=libro.nombre,
        sha256=libro.sha256,
        hojas=[
            HojaVisualRespuesta(
                nombre=h.nombre,
                visible=h.visible,
                filas=h.filas,
                columnas=h.columnas,
                anchos={str(k): v for k, v in h.anchos.items()},
                altos={str(k): v for k, v in h.altos.items()},
                ocultas_filas=list(h.ocultas_filas),
                ocultas_columnas=list(h.ocultas_columnas),
                combinadas=list(h.combinadas),
                fijas=h.fijas,
                celdas=[
                    CeldaVisualRespuesta(
                        ref=c.ref,
                        fila=c.fila,
                        columna=c.columna,
                        mostrado=c.mostrado,
                        formula=c.formula,
                        estilo=c.estilo,
                    )
                    for c in h.celdas
                ],
            )
            for h in libro.hojas
        ],
        estilos=[
            EstiloVisualRespuesta(
                relleno=e.relleno,
                fuente=e.fuente,
                tamano=e.tamano,
                negrita=e.negrita,
                cursiva=e.cursiva,
                subrayado=e.subrayado,
                color=e.color,
                alineacion_h=e.alineacion_h,
                alineacion_v=e.alineacion_v,
                ajustar_texto=e.ajustar_texto,
                formato_numero=e.formato_numero,
                bordes=e.bordes,
            )
            for e in libro.estilos
        ],
    )


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
        indicadores=indicadores_de(r.libro.totales or {}, r.totales_silice or {}),
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
    except Exception as error:  # noqa: BLE001 - frontera: nunca un 500 ni una traza al cliente
        raise _rechazo(error, MENSAJE_LIBRO, "POST /v1/libros/devolucion") from None
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


@router.post("/pdf", response_model=PdfSimpleRespuesta)
async def revisar_pdf(
    pdf: Annotated[
        UploadFile,
        File(description="Presupuesto en PDF simple, sin Excel (formato 001/002)"),
    ],
) -> PdfSimpleRespuesta:
    """Revisa solo un PDF simple (el presupuesto impreso, sin el libro de Excel): coteja el PDF
    consigo mismo (L10) y responde sus hallazgos. Sin libro no hay recálculo ni devolución. No
    guarda nada."""
    nombre = _nombre(pdf)
    _exigir_extension(nombre, ".pdf", "pdf")
    datos = await _leer(pdf, "pdf")
    try:
        r = await run_in_threadpool(auditar_pdf_simple, datos, nombre)
    except Exception as error:  # noqa: BLE001 - frontera: nunca un 500 ni una traza al cliente
        raise _rechazo(error, MENSAJE_PDF, "POST /v1/libros/pdf") from None
    leido = r.pdf
    por_severidad: dict[str, int] = {}
    for h in r.hallazgos_tabla:
        por_severidad[h.severidad] = por_severidad.get(h.severidad, 0) + 1
    return PdfSimpleRespuesta(
        pdf=PdfOrigenRespuesta(
            nombre=nombre, sha256=r.sha256, numero=leido.numero, fecha=leido.fecha
        ),
        cumple=not (por_severidad.get("CRITICO", 0) or por_severidad.get("ERROR", 0)),
        por_severidad=por_severidad,
        renglones_computos=len(leido.computos),
        renglones_presupuesto=len(leido.presupuesto),
        total_computos=_texto(leido.total_computos),
        total_impreso=_texto(leido.total_impreso),
        notas=list(leido.notas),
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
    )


@router.post("/replica", response_model=LibroVisualRespuesta)
async def replicar(
    libro: Annotated[UploadFile, File(description="Libro de la empresa (.xlsx sin macros)")],
) -> LibroVisualRespuesta:
    """Réplica visual del libro para el visor de solo lectura (RF-111): hojas en orden,
    visibilidad, anchos, altos, combinadas, ocultas, paneles fijos y, por celda, el valor mostrado,
    la fórmula y el estilo, con coordenadas de Excel (base 1). No audita ni guarda nada."""
    nombre = _nombre(libro)
    _exigir_extension(nombre, ".xlsx", "libro")
    datos = await _leer(libro, "libro")
    try:
        return await run_in_threadpool(lambda: _visual(replicar_libro(datos, nombre)))
    except Exception as error:  # noqa: BLE001 - frontera: nunca un 500 ni una traza al cliente
        raise _rechazo(error, MENSAJE_LIBRO, "POST /v1/libros/replica") from None
