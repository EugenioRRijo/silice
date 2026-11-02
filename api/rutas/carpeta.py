"""La moneda de la carpeta de trabajo y su lista para armar (MP-1, Tarea 2; D-MP1).

Rutas finas sobre `aplicacion.listas_para_armar` (la misma regla que usa Componer): una moneda por
carpeta, declarada una sola vez, y una lista vigente en esa moneda con la que se arma.

- `GET /v1/carpeta` (cualquier rol) -> `{moneda, declarada, lista, aviso}`: `moneda` es la declarada
  o, si no hay, la de la lista vigente de hoy (`null` sin ninguna); `declarada` dice si la carpeta
  la declaró; `lista` es `{nombre, moneda, fecha, origen}` de la lista vigente de hoy (`fecha` ISO)
  o `null`: la de armar o, si está en otra moneda que la carpeta, la que hay que convertir (T4: así
  la pantalla ofrece «Convertir la lista que tiene»); `aviso` es el mensaje que explica por qué no
  hay lista para armar, o `null`.
- `PUT /v1/carpeta/moneda` `{moneda: "Bs"|"USD"}` (`EDITAR_HOJA`) -> 200 con la misma forma.
  Declarar
  la que ya tiene no cambia nada. 409 «La carpeta de trabajo ya trabaja en {m}: para trabajar en
  {otra}, cree otra carpeta.» si ya hay otra declarada o la lista vigente está en otra.
- `POST /v1/carpeta/lista-para-armar` `{desde: "maprex"|"convertir"}` (`EDITAR_HOJA`) -> 201 con la
  misma forma; 409 con el mensaje de `SinListaParaArmar` (sin lista, sin tasa del BCV de los
  últimos 7 días, o nada que convertir) y, desde MaPreX, 409 «La carpeta de trabajo ya tiene lista
  para armar («{nombre}»): no se creó otra.» si ya la tiene (T4: un aviso viejo de otra pestaña no
  crea «… (2)»).

Quien declara o crea consta como la cuenta de la sesión (o `USUARIO_API` con la clave de API). Las
dos escrituras van sobre la sesión de escritura (`BEGIN IMMEDIATE`) y se confirman aquí; un error
deshace todo. Los 422 de forma no repiten lo enviado (`RutaSinEco`). Ninguna cifra viaja como
número: la ruta no devuelve montos.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.acceso import CUALQUIER_ROL
from api.dependencias import USUARIO_API, SesionDeEscrituraDep, SesionDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion.listas_para_armar import (
    CarpetaConOtraMoneda,
    SinListaParaArmar,
    crear_lista_para_armar,
    declarar_moneda_de_la_carpeta,
    describir,
    describir_vigente,
    lista_para_armar,
    moneda_de_la_carpeta,
)
from aplicacion.tablas_carpeta import CarpetaDeTrabajo
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Indique la moneda (Bs o USD) o de dónde crear la lista (maprex o convertir)."
)

#: El 409 de crear desde MaPreX con lista para armar ya creada. Componer lo reconoce por su comienzo
#: (`YA_TIENE_LISTA` de `AvisoSinLista.tsx`; lo ata `tests/unit/test_front_ya_tiene_lista.py`).
MENSAJE_YA_TIENE_LISTA = (
    "La carpeta de trabajo ya tiene lista para armar («{nombre}»): no se creó otra."
)


class _RutaCarpeta(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(prefix="/v1/carpeta", tags=["carpeta"], route_class=_RutaCarpeta)
EDITAR_HOJA = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))


class ListaDeLaCarpeta(BaseModel):
    nombre: str
    moneda: str
    fecha: str
    origen: str


class CarpetaRespuesta(BaseModel):
    moneda: str | None
    declarada: bool
    lista: ListaDeLaCarpeta | None
    aviso: str | None


class MonedaPeticion(BaseModel):
    moneda: Literal["Bs", "USD"]


class ListaPeticion(BaseModel):
    desde: Literal["maprex", "convertir"]


def _estado(sesion: Session) -> CarpetaRespuesta:
    hoy = ahora().date()
    aviso: str | None = None
    try:
        lista_para_armar(sesion, hoy)
    except SinListaParaArmar as error:
        aviso = str(error)
    # La vigente en cualquier moneda: sin aviso es la de armar; con el aviso de otra moneda, la
    # que hay que convertir.
    descrita = describir_vigente(sesion, hoy)
    return CarpetaRespuesta(
        moneda=moneda_de_la_carpeta(sesion, hoy),
        declarada=sesion.get(CarpetaDeTrabajo, 1) is not None,
        lista=None
        if descrita is None
        else ListaDeLaCarpeta(
            nombre=descrita.nombre,
            moneda=descrita.moneda,
            fecha=descrita.fecha.isoformat(),
            origen=descrita.origen,
        ),
        aviso=aviso,
    )


@router.get("", response_model=CarpetaRespuesta, dependencies=CUALQUIER_ROL)
def consultar_carpeta(sesion: SesionDep) -> CarpetaRespuesta:
    """La moneda de trabajo de la carpeta y su lista vigente de hoy: la de armar o, si está en otra
    moneda, la que hay que convertir; el aviso dice por qué no hay lista para armar."""
    return _estado(sesion)


@router.put("/moneda", response_model=CarpetaRespuesta, dependencies=[EDITAR_HOJA])
@sin_eco(MENSAJE_CUERPO_INVALIDO)
def declarar_moneda(
    sesion: SesionDeEscrituraDep,
    peticion: MonedaPeticion,
    activa: Annotated[SesionActiva | None, EDITAR_HOJA],
) -> CarpetaRespuesta:
    """Declara la moneda de trabajo de la carpeta (una sola vez: D-MP1)."""
    try:
        declarar_moneda_de_la_carpeta(
            sesion,
            peticion.moneda,
            responsable=USUARIO_API if activa is None else activa.usuario,
            ahora=ahora(),
        )
    except CarpetaConOtraMoneda as error:
        raise HTTPException(409, str(error)) from None
    sesion.commit()
    return _estado(sesion)


@router.post(
    "/lista-para-armar",
    response_model=CarpetaRespuesta,
    status_code=201,
    dependencies=[EDITAR_HOJA],
)
@sin_eco(MENSAJE_CUERPO_INVALIDO)
def crear_la_lista_para_armar(
    sesion: SesionDeEscrituraDep,
    peticion: ListaPeticion,
    activa: Annotated[SesionActiva | None, EDITAR_HOJA],
) -> CarpetaRespuesta:
    """Crea la lista para armar a partir de MaPreX o convirtiendo la vigente (tasa del BCV). Desde
    MaPreX, si la carpeta ya tiene lista para armar, 409 y no crea otra."""
    if peticion.desde == "maprex":
        ya = describir(sesion, ahora().date())
        if ya is not None:
            raise HTTPException(
                409,
                MENSAJE_YA_TIENE_LISTA.format(nombre=ya.nombre),
            )
    try:
        crear_lista_para_armar(
            sesion,
            desde=peticion.desde,
            fecha=ahora().date(),
            responsable=USUARIO_API if activa is None else activa.usuario,
        )
    except SinListaParaArmar as error:
        raise HTTPException(409, str(error)) from None
    sesion.commit()
    return _estado(sesion)
