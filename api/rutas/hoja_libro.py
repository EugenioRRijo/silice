"""`POST /v1/hoja/libro`: llevar a la Hoja el libro auditado (libro por frentes, ola 2, línea 3,
2026-11-13; `aplicacion/libro_a_la_hoja.py`).

Multipart, como la auditoría del libro (`POST /v1/libros/apu-por-hoja`): `libro` (el .xlsx con un
APU por hoja), `presupuesto` (opcional), `perfil` (opcional), `hoja_presupuesto` (una o varias
veces, opcional: las hojas del presupuesto, una por frente), `proyecto` (la obra: su código o su
nombre), `moneda` (la de los precios del libro, `Bs` o `USD`: la declara quien lo lleva) y `frente`
(sin presupuesto, el frente de todos los renglones). La ruta audita el libro con
`fusion.apu_por_hoja` (el mismo lector y el mismo perfil que la auditoría: no hay un segundo
lector) y pasa lo auditado a `aplicacion.libro_a_la_hoja`, que lo lleva al borrador de la obra sin
guardar versión. Responde el borrador, cuántos renglones quedaron, cada partida con su P.U.
impreso y el de la Hoja (a dos decimales, con punto: la pantalla los escribe en es-VE) y si casan,
y lo que no se llevó.

Como el resto de la Hoja: solo con una cuenta con `editar_hoja` (la clave de API, 403), CSRF y
`Origin` propios y `Cache-Control: no-store`. Errores: obra que no existe, 404; un libro que no se
puede leer, un perfil que no existe, ningún renglón que llevar o porcentajes distintos, 422; una
obra con versiones, otra moneda que la carpeta o que la obra, o sin lista para armar, 409; el
borrador cambió entretanto, 409; la base, 503.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.modelo import LibroNoInterpretable
from adapters.hoja_empresa.perfil import PerfilInvalido
from api.dependencias import SesionDep, url_de_la_peticion
from api.rutas import hoja as rutas_hoja
from api.rutas.hoja import MENSAJE_BASE, CuentaDeLaHoja
from api.rutas.hoja_llevar import MENSAJE_CAMBIO
from api.rutas.libros import MENSAJE_LIBRO, _exigir_extension, _leer, _nombre, _presente
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion import elaboracion, hoja_edicion, libro_a_la_hoja
from aplicacion.entrega import con_anexos_de_cadena
from aplicacion.frentes import MAX_FRENTE
from aplicacion.hoja_borradores import BorradorInexistente, RevDesactualizado
from aplicacion.proyectos import resolver_proyecto
from fusion.apu_por_hoja import ResultadoApuPorHoja, auditar_apu_por_hoja
from operacion.config import carpeta_perfiles_libros

CENTESIMA = Decimal("0.01")


class _RutaLibro(RutaSinCache, RutaSinEco):
    """Como `_RutaHoja`: `RutaSinCache` envuelve a `RutaSinEco` (si no, el 422 tendría eco)."""

    mensaje_por_omision = (
        "Lo que se lleva a la Hoja no tiene la forma esperada: envíe el libro, la obra y la "
        "moneda de sus precios."
    )


router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaLibro)


class PartidaDelLibroRespuesta(BaseModel):
    codigo: str
    codigo_libro: str
    hoja: str
    nueva: bool
    precio_impreso: str
    precio_hoja: str | None
    casa: bool


class LibroLlevadoRespuesta(BaseModel):
    """El borrador con el libro (sin guardar) y lo que se llevó."""

    borrador_id: str
    renglones: int
    partidas: list[PartidaDelLibroRespuesta]
    sin_apu: list[str]
    sin_cantidad: list[str]
    lista: str
    moneda: str


def _dos(valor: Decimal) -> str:
    return format(valor.quantize(CENTESIMA, ROUND_HALF_UP), "f")


def para_llevar(
    r: ResultadoApuPorHoja, moneda: str, frente: str | None
) -> libro_a_la_hoja.LibroParaLlevar:
    """Lo auditado como lo recibe `aplicacion.libro_a_la_hoja` (sin volver a leer el libro)."""
    apus = tuple(
        libro_a_la_hoja.ApuDelLibro(
            hoja=a.hoja,
            numero=a.numero,
            composicion=a.composicion,
            parametros=a.parametros,
            precio_impreso=a.precio_impreso,
            cantidad=a.cantidad,
            celda_cantidad=a.celda_cantidad,
            celdas_precio=a.celdas_precio,
        )
        for a in r.apus
        if a.composicion is not None and a.parametros is not None
    )
    renglones = tuple(
        libro_a_la_hoja.RenglonDelLibro(x.hoja, x.numero, x.cantidad, x.celda_cantidad)
        for x in r.renglones
    )
    return libro_a_la_hoja.LibroParaLlevar(
        archivo=r.libro.nombre, apus=apus, renglones=renglones, moneda=moneda, frente=frente
    )


@router.post("/libro", response_model=LibroLlevadoRespuesta)
async def llevar_libro(
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
    libro: Annotated[UploadFile, File(description="Libro con un APU por hoja (.xlsx)")],
    proyecto: Annotated[str, Form(min_length=1, max_length=500)],
    moneda: Annotated[Literal["Bs", "USD"], Form(description="La moneda de los precios del libro")],
    presupuesto: Annotated[UploadFile | None, File(description="Libro del presupuesto")] = None,
    perfil: Annotated[str | None, Form(max_length=200)] = None,
    hoja_presupuesto: Annotated[list[str] | None, Form()] = None,
    frente: Annotated[str | None, Form(max_length=MAX_FRENTE)] = None,
) -> LibroLlevadoRespuesta:
    """Audita el libro y lo lleva al borrador de la Hoja de la obra (ver la cabecera)."""
    nombre = _nombre(libro)
    _exigir_extension(nombre, ".xlsx", "libro")
    hay_presupuesto = _presente(presupuesto)
    nombre_presupuesto = _nombre(presupuesto) if hay_presupuesto else ""
    if hay_presupuesto:
        _exigir_extension(nombre_presupuesto, ".xlsx", "presupuesto")
    datos = await _leer(libro, "libro")
    del_presupuesto = await _leer(presupuesto, "presupuesto") if hay_presupuesto else None
    try:
        auditado = await run_in_threadpool(
            lambda: auditar_apu_por_hoja(
                datos,
                nombre,
                presupuesto=del_presupuesto,
                presupuesto_nombre=nombre_presupuesto,
                perfil=(perfil or "").strip() or "apu_por_hoja",
                carpeta_perfiles=carpeta_perfiles_libros(),
                hojas=tuple(hoja_presupuesto or ()),
            )
        )
    except (PerfilInvalido, ArchivoRechazado, LibroNoInterpretable) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except Exception:  # noqa: BLE001 - frontera: nunca un 500 con traza
        raise HTTPException(status_code=422, detail=MENSAJE_LIBRO) from None
    sin_presupuesto = None if hay_presupuesto else (frente or "").strip() or None
    para = para_llevar(auditado, moneda, sin_presupuesto)
    try:
        con_anexos_de_cadena(sesion)
        obra = resolver_proyecto(sesion, proyecto)
        if obra is None:
            raise HTTPException(status_code=404, detail=elaboracion.MENSAJE_SIN_OBRA)
        llevado = libro_a_la_hoja.llevar_libro_a_la_hoja(
            sesion,
            activa.huella_ficha,
            url_de_la_peticion(request),
            obra,
            para,
            responsable=activa.usuario,
            hoy=rutas_hoja._hoy(),
        )
    except (libro_a_la_hoja.LibroSinRenglones, libro_a_la_hoja.PorcentajesDistintos) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except (
        libro_a_la_hoja.ObraConVersiones,
        libro_a_la_hoja.MonedaDistinta,
        hoja_edicion.SinListaDeLaObra,
        elaboracion.VersionQueNoSeAbre,
    ) as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except (hoja_edicion.BorradorYaGuardado, RevDesactualizado, BorradorInexistente):
        raise HTTPException(status_code=409, detail=MENSAJE_CAMBIO) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    except ValueError as error:  # SinListaParaArmar: la carpeta no tiene lista para armar
        raise HTTPException(status_code=409, detail=str(error)) from None
    return LibroLlevadoRespuesta(
        borrador_id=llevado.borrador_id,
        renglones=llevado.renglones,
        partidas=[
            PartidaDelLibroRespuesta(
                codigo=p.codigo,
                codigo_libro=p.codigo_libro,
                hoja=p.hoja,
                nueva=p.nueva,
                precio_impreso=_dos(p.precio_impreso),
                precio_hoja=None if p.precio_hoja is None else _dos(p.precio_hoja),
                casa=p.casa,
            )
            for p in llevado.partidas
        ],
        sin_apu=list(llevado.sin_apu),
        sin_cantidad=list(llevado.sin_cantidad),
        lista=llevado.lista,
        moneda=llevado.moneda,
    )
