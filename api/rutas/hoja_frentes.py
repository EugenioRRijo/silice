"""El presupuesto de la Hoja agrupado por frente (libro por frentes, ola 2, línea 3, 2026-11-13;
`aplicacion/frentes.py`).

- `GET /v1/hoja/borradores/{id}/vistas/frentes`: el subtotal de cada frente y el total general,
  calculados por el servidor (la pantalla solo los muestra), en el orden en que aparece cada frente
  y con los renglones sin frente al final (`frente: null`). Lo ve quien arma y quien revisa.
- `PUT /v1/hoja/borradores/{id}/frentes` `{rev, filas: [{clave, frente}]}`: pone (o, vacío, quita)
  el frente de renglones propios del borrador. Devuelve el `rev` nuevo, el resumen y los frentes.
  Solo con una cuenta con `editar_hoja`; una clave que no es de un renglón propio, 422; un `rev`
  viejo, 409.

Los frentes de un renglón viajan con él como la directiva `_frente` de sus especificaciones, así
que se guardan y vuelven con la versión. En router aparte para no tocar `api/rutas/hoja.py`: reusa
de allí el borrador de la ficha (`_vivo`) y el esqueleto de las ediciones (`_editar`).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from api.dependencias import SesionDep
from api.esquemas_hoja import (
    MontoHojaRespuesta,
    ResumenHojaRespuesta,
    monto_a_respuesta,
    resumen_a_respuesta,
)
from api.rutas.hoja import (
    CuentaDeLaHoja,
    CuentaQueVe,
    IdDeBorrador,
    _editar,
    _RutaHoja,
    _vivo,
)
from api.sin_eco import sin_eco
from aplicacion import frentes, hoja_edicion, hoja_vista
from aplicacion.frentes import MAX_FRENTE

FORMA_FRENTES = (
    "Los frentes enviados no tienen la forma esperada: envíe el rev y, por renglón, su clave y su "
    f"frente (hasta {MAX_FRENTE} caracteres)."
)

router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaHoja)


class FilaDeFrente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clave: Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    frente: Annotated[str, Field(strict=True, max_length=MAX_FRENTE)] = ""


class EdicionFrentes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rev: Annotated[int, Field(strict=True, ge=0)]
    filas: Annotated[list[FilaDeFrente], Field(max_length=5000)]


class FrenteRespuesta(BaseModel):
    """Un frente: su nombre (`null`: los renglones sin frente), sus renglones, los pendientes (sin
    APU, no suman) y su subtotal."""

    frente: str | None
    renglones: int
    pendientes: int
    total: MontoHojaRespuesta


class VistaFrentesRespuesta(BaseModel):
    rev: int
    frentes: list[FrenteRespuesta]
    total: MontoHojaRespuesta
    con_frentes: bool


class EdicionFrentesRespuesta(BaseModel):
    rev: int
    resumen: ResumenHojaRespuesta
    frentes: VistaFrentesRespuesta


def _vista(rev: int, por: frentes.PresupuestoPorFrentes) -> VistaFrentesRespuesta:
    return VistaFrentesRespuesta(
        rev=rev,
        frentes=[
            FrenteRespuesta(
                frente=f.frente,
                renglones=f.renglones,
                pendientes=f.pendientes,
                total=monto_a_respuesta(hoja_vista.monto(f.total)),
            )
            for f in por.frentes
        ],
        total=monto_a_respuesta(hoja_vista.monto(por.total)),
        con_frentes=por.con_frentes,
    )


@router.get("/borradores/{id}/vistas/frentes", response_model=VistaFrentesRespuesta)
def vista_frentes(id: IdDeBorrador, request: Request, activa: CuentaQueVe) -> VistaFrentesRespuesta:
    """El presupuesto agrupado por frente, con el cálculo del `rev` de ahora."""
    vivo = _vivo(request, activa, id)
    with vivo.cerrojo:
        resultado, _ = hoja_vista.calculo(vivo)
        return _vista(vivo.rev, frentes.por_frentes(resultado))


@router.put("/borradores/{id}/frentes", response_model=EdicionFrentesRespuesta)
@sin_eco(FORMA_FRENTES)
def editar_frentes(
    id: IdDeBorrador,
    datos: EdicionFrentes,
    request: Request,
    activa: CuentaDeLaHoja,
    sesion: SesionDep,
) -> EdicionFrentesRespuesta:
    """Pone el frente de los renglones enviados y devuelve los frentes recalculados."""
    vivo = _vivo(request, activa, id)
    mapa = {fila.clave: fila.frente for fila in datos.filas}
    resumen, vista = _editar(
        sesion,
        vivo,
        lambda: hoja_edicion.cambiar_borrador(
            sesion,
            activa.huella_ficha,
            id,
            datos.rev,
            lambda actual: frentes.poner_frentes(actual.borrador, mapa),
        ),
        lambda editado: _vista(editado.rev, frentes.por_frentes(hoja_vista.calculo(editado)[0])),
    )
    return EdicionFrentesRespuesta(
        rev=resumen.rev, resumen=resumen_a_respuesta(resumen), frentes=vista
    )
