"""`/v1/reajuste/*`: «Reajuste de precios» por HTTP (ola 4 de la sesión 2b; UC-18, RF-71 y RF-72).

Es `ui/paginas/reajuste.py` hecha servicio sobre `aplicacion.reajuste` (la misma lógica que usa
Streamlit; los mensajes de error son los suyos). Todas las rutas exigen `CONVERTIR_Y_REAJUSTAR`
(rol arma) con sesión o clave de API (RM-3) y trabajan sobre el caso de la sesión (`SesionDep`):

- `GET /contexto?proyecto=` → versiones (con su motivo y si son revaloradas, las que sirven a la
  comprobación directa) y las opciones de los desplegables.
- `GET /parciales?proyecto=&version=` → estudios «parcial al corte» que un cerrado puede reemplazar.
- `POST /calcular` → la tabla lado a lado como texto, avisos y estado; **no escribe**.
- `POST /guardar` → guarda el estudio y confirma; dice su número y su estado.
- `POST /excel` → el libro de la versión con las hojas Reajuste y Ejecutado.

Sin estado en el servidor: cada POST trae la cláusula, los componentes, los periodos y lo
ejecutado, y la ruta vuelve a calcular (lo que se ve es lo que se guardaría, como en la pantalla).
Un dato malo es 422 con el mensaje de la pantalla clásica. Con `con_valuaciones` lo ejecutado sale
de las valuaciones registradas y no anuladas (RF-72) y `ejecutado` se ignora. Montos y tasas viajan
como texto (NORMAS.md, regla 3); el navegador no calcula nada. Un 422 de forma del cuerpo no repite
lo enviado (`RutaSinEco`). «Responsable» en blanco es la persona de la sesión.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.dependencias import SesionDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_eco import RutaSinEco
from aplicacion import reajuste as logica
from aplicacion.errores import HojaInvalida
from core import models
from core.budget.reajuste import COMPONENTES, EstadoEstudio, Estructura, Mecanismo
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Los datos del estudio no tienen la forma esperada: escriba cada campo como texto."
)
MENSAJE_NUMERO_ENORME = "Un número del estudio es demasiado grande o no es válido."
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SIN_CACHE = {"Cache-Control": "no-store"}
PERIODICIDADES = ["mensual", "trimestral"]  # las que ofrece la pantalla clásica

REAJUSTAR = Depends(exigir_clave_o_sesion(Accion.CONVERTIR_Y_REAJUSTAR))


class _RutaReajuste(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(
    prefix="/v1/reajuste", tags=["reajuste"], route_class=_RutaReajuste, dependencies=[REAJUSTAR]
)

Texto = Annotated[str, Field(max_length=500)]
Fila = dict[Texto, Texto]


# --- Esquemas -----------------------------------------------------------------------------


class ClausulaTextos(BaseModel):
    """Los campos de la cláusula como los escribe la persona (S1 §8.1); se validan al calcular."""

    fecha_inicio: Texto = ""
    duracion_meses: Texto = ""
    fecha_referencia_primer_anio: Texto = ""
    periodicidad: Texto = ""
    mecanismo: Texto = ""
    mecanismo_pagadero: Texto = ""
    fuente_pagadero: Texto = ""
    estructura: Texto = ""
    fecha_base_indices: Texto = ""
    r: Texto = ""
    fuente_r: Texto = ""
    r_en_comprobacion: Texto = "no"
    fuente: Texto = ""
    responsable: Texto = ""


class EstudioPeticion(BaseModel):
    proyecto: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=40)
    clausula: ClausulaTextos
    componentes: list[Fila] = Field(default_factory=list, max_length=20)
    periodos: list[Fila] = Field(default_factory=list, max_length=500)
    ejecutado: list[Fila] = Field(default_factory=list, max_length=5000)
    con_valuaciones: bool = False


class GuardarPeticion(EstudioPeticion):
    fuente: Texto = ""
    responsable: Texto = ""
    reemplaza_a: int | None = None


class VersionRespuesta(BaseModel):
    codigo: str
    motivo: str
    revalorada: bool


class ContextoRespuesta(BaseModel):
    versiones: list[VersionRespuesta]
    periodicidades: list[str]
    mecanismos: list[str]
    estructuras: list[str]
    componentes: list[str]


class ParcialRespuesta(BaseModel):
    id: int
    fecha_calculo: str


class CalculoRespuesta(BaseModel):
    estado: str
    moneda: str
    columnas: list[str]
    filas: list[dict[str, str]]
    avisos: list[str]
    mensaje_parcial: str
    parciales: list[ParcialRespuesta]


class GuardadoRespuesta(BaseModel):
    estudio: int
    estado: str


# --- Ayudas -------------------------------------------------------------------------------


def _proyecto_existente(sesion, nombre: str) -> None:
    if (
        sesion.scalars(select(models.Proyecto).where(models.Proyecto.nombre == nombre)).first()
        is None
    ):
        raise HTTPException(404, f"El proyecto «{nombre}» no existe en este caso.")


def _quien(activa: SesionActiva | None) -> str:
    return "" if activa is None else activa.usuario


def _preparar(sesion, p: EstudioPeticion, activa: SesionActiva | None):
    """Cláusula, periodos y resultado en memoria (nada queda escrito). `HojaInvalida` → 422."""
    campos = p.clausula.model_dump()
    campos["responsable"] = campos["responsable"].strip() or _quien(activa)
    try:
        clausula = logica.clausula_desde_textos(campos, p.componentes)
        if p.con_valuaciones:
            periodos = logica.periodos_desde_valuaciones(sesion, p.proyecto, p.periodos)
        else:
            periodos = logica.periodos_desde_filas(p.periodos, p.ejecutado)
        resultado = logica.calcular(
            sesion, p.proyecto, p.version, clausula, periodos, fecha_calculo=ahora().date()
        )
    except HojaInvalida as error:
        raise HTTPException(422, str(error)) from None
    except ArithmeticError:  # Decimal fuera de rango, exponentes enormes
        raise HTTPException(422, MENSAJE_NUMERO_ENORME) from None
    return clausula, periodos, resultado


def _parciales(sesion, proyecto: str, version: str) -> list[ParcialRespuesta]:
    try:
        lista = logica.parciales_por_reemplazar(sesion, proyecto, version)
    except HojaInvalida as error:
        raise HTTPException(404, str(error)) from None
    return [ParcialRespuesta(id=i, fecha_calculo=f.isoformat()) for i, f in lista]


def nombre_excel(version: str) -> str:
    """`reajuste_<version>.xlsx` con solo caracteres seguros para una cabecera."""
    return f"reajuste_{re.sub(r'[^A-Za-z0-9._-]', '_', version)}.xlsx"


# --- Rutas --------------------------------------------------------------------------------


@router.get("/contexto", response_model=ContextoRespuesta)
def contexto(
    sesion: SesionDep, response: Response, proyecto: Annotated[str, Query(max_length=200)]
) -> ContextoRespuesta:
    """Las versiones del proyecto (de la más antigua a la más reciente) y las opciones."""
    response.headers.update(SIN_CACHE)
    _proyecto_existente(sesion, proyecto)
    return ContextoRespuesta(
        versiones=[
            VersionRespuesta(codigo=c, motivo=m, revalorada=m == "revaloracion")
            for c, m in logica.versiones_del_proyecto(sesion, proyecto)
        ],
        periodicidades=PERIODICIDADES,
        mecanismos=[m.value for m in Mecanismo],
        estructuras=[e.value for e in Estructura],
        componentes=list(COMPONENTES),
    )


@router.get("/parciales", response_model=list[ParcialRespuesta])
def parciales(
    sesion: SesionDep,
    response: Response,
    proyecto: Annotated[str, Query(max_length=200)],
    version: Annotated[str, Query(max_length=40)],
) -> list[ParcialRespuesta]:
    response.headers.update(SIN_CACHE)
    _proyecto_existente(sesion, proyecto)
    return _parciales(sesion, proyecto, version)


@router.post("/calcular", response_model=CalculoRespuesta)
def calcular(
    sesion: SesionDep,
    peticion: EstudioPeticion,
    response: Response,
    activa: Annotated[SesionActiva | None, REAJUSTAR],
) -> CalculoRespuesta:
    response.headers.update(SIN_CACHE)
    _, _, resultado = _preparar(sesion, peticion, activa)
    return _respuesta(sesion, peticion, resultado)


def _respuesta(sesion, p: EstudioPeticion, resultado) -> CalculoRespuesta:
    parcial = ""
    if resultado.estado is EstadoEstudio.PARCIAL:
        parcial = (
            f"El último período aún no cierra: el estudio se guardará «parcial al corte» al "
            f"{resultado.fecha_corte:%d/%m/%Y} y se reemplaza al cerrar el mes."
        )
    return CalculoRespuesta(
        estado=resultado.estado.value,
        moneda=resultado.moneda,
        columnas=list(logica.COLUMNAS_REAJUSTE),
        filas=logica.filas_lado_a_lado(resultado),
        avisos=list(resultado.avisos),
        mensaje_parcial=parcial,
        parciales=_parciales(sesion, p.proyecto, p.version)
        if resultado.estado is EstadoEstudio.CERRADO
        else [],
    )


@router.post("/guardar", response_model=GuardadoRespuesta)
def guardar(
    sesion: SesionDep,
    peticion: GuardarPeticion,
    response: Response,
    activa: Annotated[SesionActiva | None, REAJUSTAR],
) -> GuardadoRespuesta:
    response.headers.update(SIN_CACHE)
    clausula, periodos, resultado = _preparar(sesion, peticion, activa)
    responsable = peticion.responsable.strip() or _quien(activa)
    opciones = {
        "fecha_calculo": ahora().date(),
        "fuente": peticion.fuente,
        "responsable": responsable,
        "reemplaza_a": peticion.reemplaza_a if resultado.estado is EstadoEstudio.CERRADO else None,
    }
    try:
        if peticion.con_valuaciones:
            estudio = logica.guardar_con_valuaciones(
                sesion, peticion.proyecto, peticion.version, clausula, peticion.periodos, **opciones
            )
        else:
            estudio = logica.guardar(
                sesion, peticion.proyecto, peticion.version, clausula, periodos, **opciones
            )
    except HojaInvalida as error:
        raise HTTPException(422, str(error)) from None
    except ArithmeticError:
        raise HTTPException(422, MENSAJE_NUMERO_ENORME) from None
    return GuardadoRespuesta(estudio=estudio, estado=resultado.estado.value)


@router.post("/excel", response_class=Response, responses={200: {"content": {XLSX: {}}}})
def excel(
    sesion: SesionDep,
    peticion: EstudioPeticion,
    activa: Annotated[SesionActiva | None, REAJUSTAR],
) -> Response:
    _, periodos, resultado = _preparar(sesion, peticion, activa)
    try:
        contenido = logica.excel_en_bytes(
            sesion, peticion.proyecto, peticion.version, resultado, periodos
        )
    except (HojaInvalida, ValueError) as error:
        detalle = logica.con_tildes_de_reajuste(str(error))
        raise HTTPException(422, f"No se pudo preparar el Excel: {detalle}") from None
    return Response(
        content=contenido,
        media_type=XLSX,
        headers={
            **SIN_CACHE,
            "Content-Disposition": f'attachment; filename="{nombre_excel(peticion.version)}"',
        },
    )
