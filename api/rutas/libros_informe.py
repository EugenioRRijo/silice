"""`POST /v1/libros/auditoria/pdf`: el informe de hallazgos de un libro en PDF (UC-25; P2 del Word
del 2026-11-19, elegida por Claude con Eugenio ausente y conservada por él, acta DS-77).

Recibe lo mismo que `POST /v1/libros/auditoria` (el libro `.xlsx` y la `fecha_devolucion`), audita
de nuevo con esa fecha (misma fecha, mismo resultado) y responde el PDF que dibuja
`aplicacion.hallazgos_pdf`. Es la ruta que sirve el botón «Descargar PDF» del visor de
«Libro de la empresa».

No guarda nada: ni el libro ni el PDF (RNF-28), y tampoco deja una fila nueva en el historial: la
auditoría que la persona ve en pantalla ya dejó la suya, y bajar el informe no es auditar otra vez.
Mismo acceso que las demás rutas de libros (clave de API, o cuenta que arma o revisa; lo exige
`api.main`). Errores: `{"detalle": ...}`; un fallo propio es 500 con un mensaje fijo.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from api.rutas.libros import INDICADORES, ContextoDep, EntradaDep, _ahora, _procesar, _rechazo
from api.sin_cache import RutaSinCache
from aplicacion.hallazgos_pdf import (
    FilaDeHallazgo,
    InformeDeHallazgos,
    LineaDeTotal,
    conteo_por_severidad,
    dinero,
    nombre_del_pdf_de_hallazgos,
    pdf_de_hallazgos,
    severidad_escrita,
)
from fusion.proceso import ResultadoFusion

router = APIRouter(prefix="/v1/libros", tags=["libros"], route_class=RutaSinCache)

TIPO_PDF = "application/pdf"
MENSAJE_PDF_HALLAZGOS = "No se pudo preparar el PDF de hallazgos."
SIN_FECHA = "sin fecha"
SIN_TOTAL = "—"
#: Cuántos caracteres del SHA-256 del libro lleva el PDF.
HUELLA_ABREVIADA = 12


def _dia(valor: date | None) -> str:
    return SIN_FECHA if valor is None else valor.strftime("%d/%m/%Y")


def informe_de(r: ResultadoFusion, emitido: date) -> InformeDeHallazgos:
    """Las mismas cifras que la pantalla, ya escritas: totales del libro frente a los de Sílice y
    una fila por hallazgo, en el orden de la tabla de la auditoría."""
    libro, silice = r.libro.totales or {}, r.totales_silice or {}
    totales = tuple(
        LineaDeTotal(
            titulo,
            SIN_TOTAL if libro.get(clave) is None else dinero(libro[clave]),
            SIN_TOTAL if silice.get(clave) is None else dinero(silice[clave]),
        )
        for clave, titulo in INDICADORES.items()
        if libro.get(clave) is not None or silice.get(clave) is not None
    )
    return InformeDeHallazgos(
        libro=r.libro.nombre,
        fecha_libro=_dia(r.fecha_libro),
        fecha_devolucion=_dia(r.fecha_devolucion),
        emitido=_dia(emitido),
        veredicto="Cumple" if r.informe.cumple else "No cumple",
        conteo=conteo_por_severidad(h.severidad for h in r.hallazgos_tabla),
        totales=totales,
        huella=r.libro.sha256[:HUELLA_ABREVIADA],
        hallazgos=tuple(
            FilaDeHallazgo(
                codigo=h.codigo,
                severidad=severidad_escrita(h.severidad),
                celda=h.celda,
                descripcion=h.descripcion,
                impacto="" if h.impacto is None else dinero(h.impacto),
                accion=h.accion,
            )
            for h in r.hallazgos_tabla
        ),
    )


@router.post(
    "/auditoria/pdf",
    response_class=Response,
    responses={200: {"content": {TIPO_PDF: {}}, "description": "El PDF de hallazgos."}},
)
async def pdf_de_la_auditoria(entrada: EntradaDep, contexto: ContextoDep) -> Response:
    """El informe de hallazgos del libro en PDF: libro, fechas, resultado, totales y cada hallazgo.
    No guarda nada ni toca el historial."""
    r = await _procesar(entrada, contexto)
    emitido = _ahora().date()
    try:
        contenido = await run_in_threadpool(lambda: pdf_de_hallazgos(informe_de(r, emitido)))
    except Exception as error:  # noqa: BLE001 - frontera: nunca un 500 con traza al cliente
        raise _rechazo(error, MENSAJE_PDF_HALLAZGOS, "POST /v1/libros/auditoria/pdf") from None
    nombre = nombre_del_pdf_de_hallazgos(entrada.nombre)
    return Response(
        content=contenido,
        media_type=TIPO_PDF,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
