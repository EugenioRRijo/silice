"""`/v1/hoja/borradores/{id}/plano`: importar un plano DXF o IFC a la hoja (T10, 3e-2; P1 a P6).

Es el flujo «Importar plano (DXF o IFC)» de la pagina clasica hecho servicio sobre
`aplicacion.hoja_plano` (contrato: `docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md`):

- P1 `POST .../plano` (multipart: `archivo` y `rev`) lee el plano y deja la importacion vigente;
- P2 `POST .../plano/unidad`, P3 `.../plano/alturas` y P4 `.../plano/circuitos` la cambian;
- P5 `POST .../plano/fusionar` la funde con el espacio del borrador (sube `rev`) y la descarta;
- P6 `DELETE .../plano` la descarta (204, idempotente).

Las reglas son las del resto de los borradores (`api/rutas/hoja.py`, de donde se toman el acceso
«solo cuenta» con `EDITAR_HOJA`, el id y `_vivo`): un borrador de otra ficha no existe (404), uno de
otro caso da 409, `rev` se comprueba antes que el contenido (409), todo `no-store` y el 422 de forma
no repite lo enviado (`_RutaPlano` combina `RutaSinCache` y `RutaSinEco` en ESE orden). El tope de
20 MiB es el de `LimiteDeCuerpo` (413 tambien por trozos); no hay middleware propio.

Topes del lector (ola de decisiones, `aplicacion.hoja_plano`): un plano de mas bytes que el maximo
de su formato (DXF 8 MiB, IFC 20 MiB) es 413 de texto fijo; con `LECTURAS_SIMULTANEAS` planos ya
leyendose, P1 y P2 responden 503 de texto fijo con `Retry-After` sin esperar (asi el grupo de hilos
de las rutas sincronas no se agota); al arrancar se barren las carpetas huerfanas.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import SesionDep
from api.esquemas_hoja import resumen_a_respuesta
from api.esquemas_hoja_plano import (
    AlturasDelPlano,
    CircuitosDelPlano,
    FusionDelPlano,
    FusionRespuesta,
    ImportacionRespuesta,
    UnidadDelPlano,
)
from api.rutas.hoja import (
    FORMA_REV,
    MENSAJE_BASE,
    MENSAJE_FALTA,
    MENSAJE_REV,
    CuentaDeLaHoja,
    IdDeBorrador,
    _mas_nueva,
    _vivo,
)
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import hoja, hoja_edicion, hoja_plano, hoja_vista
from aplicacion.hoja_borradores import BorradorInexistente, RevDesactualizado

FORMA_PLANO = "Suba un archivo de plano (DXF o IFC) y envíe el rev del borrador."
FORMA_UNIDAD = (
    "La unidad no tiene la forma esperada: envíe el rev del borrador (un número entero) y la "
    "unidad del dibujo como texto."
)
FORMA_ALTURAS = (
    "Las alturas no tienen la forma esperada: envíe el rev y, por cada ambiente, su altura como "
    "texto de hasta 500 caracteres, con no más de 5000 ambientes."
)
FORMA_CIRCUITOS = (
    "Los circuitos no tienen la forma esperada: envíe el rev y, por cada circuito, cuatro textos "
    "(fase, neutro, tierra y puntos máximos) de hasta 500 caracteres, con no más de 5000 "
    "circuitos."
)


class _RutaPlano(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (diseño §1.3-7)."""

    mensaje_por_omision = FORMA_PLANO


#: Segundos que se sugieren esperar cuando ya hay `LECTURAS_SIMULTANEAS` planos leyendose.
REINTENTAR_EN = "10"

# `on_startup`: al arrancar el servidor se barren las carpetas `silice_planos_*` que dejo un proceso
# caido (el plano de una persona no debe quedar para siempre en el disco).
router = APIRouter(
    prefix="/v1/hoja",
    tags=["hoja"],
    route_class=_RutaPlano,
    on_startup=[hoja_plano.barrer_al_arrancar],
)


class _Subida:
    """Lo que `aplicacion.subidas.guardar_subida` usa de una subida: su nombre y sus bytes."""

    def __init__(self, archivo: UploadFile) -> None:
        self.name = archivo.filename or ""
        self._archivo = archivo

    def getvalue(self) -> bytes:
        self._archivo.file.seek(0)
        return self._archivo.file.read()


async def _un_solo_archivo(request: Request) -> None:
    """Un `archivo` repetido no se elige en silencio: es un 422 de forma (sin eco)."""
    formulario = await request.form()  # el que FastAPI ya leyo (queda en la peticion)
    if len(formulario.getlist("archivo")) > 1:
        raise RequestValidationError(
            [{"type": "too_long", "loc": ("body", "archivo"), "msg": "un solo archivo"}]
        )


@contextmanager
def _traducir() -> Iterator[None]:
    """Los errores de la importacion como respuesta: 404, 409, 422 (el texto de la clasica) y 503
    (sin el `orig` del driver)."""
    try:
        yield
    except BorradorInexistente:
        raise HTTPException(status_code=404, detail=MENSAJE_FALTA) from None
    except RevDesactualizado:
        raise HTTPException(status_code=409, detail=MENSAJE_REV) from None
    except hoja_edicion.BorradorYaGuardado as error:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Este borrador ya se guardó como la versión {error.codigo}; "
                "abra esa versión para seguir."
            ),
        ) from None
    except hoja_plano.PlanoDemasiadoGrande as error:
        raise HTTPException(status_code=413, detail=error.mensaje) from None
    except hoja_plano.LecturasOcupadas:
        raise HTTPException(
            status_code=503,
            detail=hoja_plano.MENSAJE_LECTURAS_OCUPADAS,
            headers={"Retry-After": REINTENTAR_EN},
        ) from None
    except hoja_plano.SinImportacion:
        raise HTTPException(status_code=409, detail=hoja_plano.MENSAJE_SIN_IMPORTACION) from None
    except hoja_plano.NoDetenida:
        raise HTTPException(status_code=409, detail=hoja_plano.MENSAJE_NO_DETENIDA) from None
    except hoja_plano.ImportacionNoFusionable as error:
        raise HTTPException(status_code=409, detail=error.mensaje) from None
    except ValueError as error:  # `HojaInvalida` y el espacio que no vale: el texto del dominio
        raise HTTPException(status_code=422, detail=str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None


def _importacion(resultado) -> ImportacionRespuesta:
    return ImportacionRespuesta(**hoja_plano.vista_de_importacion(resultado))


@router.post("/borradores/{id}/plano", response_model=ImportacionRespuesta)
@sin_eco(FORMA_PLANO)
def leer_plano(
    id: IdDeBorrador,
    request: Request,
    activa: CuentaDeLaHoja,
    _uno: Annotated[None, Depends(_un_solo_archivo)],
    archivo: Annotated[UploadFile, File()],
    rev: Annotated[int, Form(ge=0)],
) -> ImportacionRespuesta:
    """P1: guarda el plano en una carpeta temporal del borrador y lo lee. La extension se mira
    ANTES de escribir; un archivo corrupto es `estado: "rechazada"` con 200. No cambia el borrador
    ni su `rev`; reemplaza la importacion anterior."""
    vivo = _vivo(request, activa, id)
    with _traducir():
        return _importacion(hoja_plano.leer(vivo, rev, _Subida(archivo)))


@router.post("/borradores/{id}/plano/unidad", response_model=ImportacionRespuesta)
@sin_eco(FORMA_UNIDAD)
def reanudar_con_unidad(
    id: IdDeBorrador, datos: UnidadDelPlano, request: Request, activa: CuentaDeLaHoja
) -> ImportacionRespuesta:
    """P2: vuelve a leer el plano detenido con la unidad del dibujo (m, cm, mm, dm, in o ft)."""
    vivo = _vivo(request, activa, id)
    with _traducir():
        return _importacion(hoja_plano.reanudar(vivo, datos.rev, datos.unidades))


@router.post("/borradores/{id}/plano/alturas", response_model=ImportacionRespuesta)
@sin_eco(FORMA_ALTURAS)
def cargar_alturas(
    id: IdDeBorrador, datos: AlturasDelPlano, request: Request, activa: CuentaDeLaHoja
) -> ImportacionRespuesta:
    """P3: carga las alturas de los ambientes pendientes, todo o nada (en blanco, pendiente)."""
    vivo = _vivo(request, activa, id)
    with _traducir():
        return _importacion(hoja_plano.cargar_alturas(vivo, datos.rev, datos.alturas))


@router.post("/borradores/{id}/plano/circuitos", response_model=ImportacionRespuesta)
@sin_eco(FORMA_CIRCUITOS)
def declarar_circuitos(
    id: IdDeBorrador, datos: CircuitosDelPlano, request: Request, activa: CuentaDeLaHoja
) -> ImportacionRespuesta:
    """P4: declara los circuitos supuestos (fase, neutro, tierra, puntos maximos), todo o nada."""
    vivo = _vivo(request, activa, id)
    with _traducir():
        return _importacion(hoja_plano.declarar_circuitos(vivo, datos.rev, datos.circuitos))


@router.post("/borradores/{id}/plano/fusionar", response_model=FusionRespuesta)
@sin_eco(FORMA_REV)
def fusionar_plano(
    id: IdDeBorrador,
    datos: FusionDelPlano,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> FusionRespuesta:
    """P5: funde la importacion con el espacio del borrador (completa las composiciones como la
    edicion del espacio y sube `rev`) y la descarta. Detenida o rechazada, 409; sin importacion,
    409; un espacio que no vale, 422 y el borrador intacto."""
    vivo = _vivo(request, activa, id)
    with _traducir(), vivo.cerrojo:  # el resumen es el del `rev` que produjo ESTA fusion
        fusion = hoja_plano.fusionar(sesion, vivo, datos.rev)
        editado = fusion.vivo
        mas_nueva = _mas_nueva(editado, hoja.codigo_vigente(sesion, editado.proyecto))
        resumen = hoja_vista.resumen(editado, mas_nueva)
    return FusionRespuesta(
        rev=resumen.rev,
        resumen=resumen_a_respuesta(resumen),
        **hoja_plano.vista_de_fusion(fusion),
    )


@router.delete("/borradores/{id}/plano", status_code=204, response_class=Response)
def descartar_plano(id: IdDeBorrador, request: Request, activa: CuentaDeLaHoja) -> Response:
    """P6: descarta la importacion y su carpeta temporal. Idempotente; no cambia el borrador."""
    hoja_plano.descartar(_vivo(request, activa, id))
    return Response(status_code=204)
