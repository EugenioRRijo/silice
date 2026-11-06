"""`/v1/simulador`: el simulador de listas de precios de la interfaz nueva (migracion de la pagina
Streamlit «Simulador de listas»; herramienta de prueba, no fuente de mercado, UC-07 es I6.3).

Dos POST con el mismo cuerpo, que **no escriben** en la base (solo leen la lista vigente del caso):

- `POST /v1/simulador` `{semilla, variacion_max, insumos}` -> `{filas: [{tipo, insumo, unidad,
  precio}]}`; los precios viajan como texto decimal exacto. Sin filas (filtro que no coincide) es
  200 con `filas: []`: la pantalla dice el mensaje.
- `POST /v1/simulador/csv` mismo cuerpo -> `text/csv` (`lista_simulada.csv`, columnas
  `tipo,insumo,unidad,precio`, el formato que consume UC-02). Sin filas, 422 con el mensaje de la
  pagina Streamlit.

`semilla` es un entero >= 0; `variacion_max` es un decimal en porcentaje escrito como texto;
`insumos` son descripciones separadas por coma o, desde el autocompletado, una lista de
descripciones exactas, que admite una con coma. `null` (u omitido) y el texto vacio son todos;
un texto de solo comas y espacios o una lista sin nombres (`[]` incluida) es ninguno (0 filas;
las reglas en `aplicacion.simulador.insumos_de_texto`). Topes: el texto, 20.000 caracteres (el
de siempre); la lista, 200 descripciones de hasta 500 caracteres y 20.000 en total, el mismo
orden que el texto. Errores como en Streamlit, en `{"detalle": ...}`: variacion no decimal o
valores invalidos, 422; sin lista vigente, 409. El 422 de validacion del esquema es el de
FastAPI (`{"detail": [...]}`) sin el `input` de cada error: no repite lo enviado. El acceso lo
exige cada ruta con `api.acceso.EDITAR` (clave o sesion con `EDITAR_HOJA`, RM-3). El caso es el
de la sesion web (RM-2): lo resuelve `api.dependencias.SesionDep`.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, field_validator

from api.acceso import EDITAR
from api.dependencias import SesionDep
from aplicacion.simulador import (
    MENSAJE_SIN_FILAS,
    NOMBRE_CSV,
    csv_de,
    simular_desde_catalogo,
)


class _RutaSinEntradaEnEl422(APIRoute):
    """El 422 de validacion de FastAPI de siempre, sin el `input` de cada error: una lista de
    insumos rechazada por el tope no vuelve entera en la respuesta."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejador(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError as error:
                errores = [
                    {clave: valor for clave, valor in e.items() if clave != "input"}
                    for e in error.errors()
                ]
                raise RequestValidationError(errores) from None

        return manejador


router = APIRouter(prefix="/v1/simulador", tags=["simulador"], route_class=_RutaSinEntradaEnEl422)

#: Tope de `int64`: lo que admite el campo numerico de la pagina Streamlit.
SEMILLA_MAXIMA = 2**63 - 1

#: Tope del texto de insumos (el de siempre) y del total de caracteres de la lista.
TOPE_DE_CARACTERES = 20000
#: Tope de descripciones de la lista: la pantalla las elige una a una con el autocompletado;
#: para mas, «todos» (`null`). 200 x 500 caracteres cabe en el mismo orden que el texto, y el
#: total lo corta `TOPE_DE_CARACTERES`.
TOPE_DE_INSUMOS = 200
LARGO_DE_UN_INSUMO = 500
MENSAJE_TOPE_DE_CARACTERES = (
    f"La lista de insumos no puede pasar de {TOPE_DE_CARACTERES} caracteres en total."
)

TextoDeInsumos = Annotated[str, Field(max_length=TOPE_DE_CARACTERES)]
ListaDeInsumos = Annotated[
    list[Annotated[str, Field(max_length=LARGO_DE_UN_INSUMO)]],
    Field(max_length=TOPE_DE_INSUMOS),
]


class SimulacionPeticion(BaseModel):
    semilla: int = Field(42, ge=0, le=SEMILLA_MAXIMA, strict=True)
    variacion_max: str = Field("5", max_length=40, description="Porcentaje, decimal como texto")
    insumos: TextoDeInsumos | ListaDeInsumos | None = Field(
        None,
        description=(
            "Separados por coma, o una lista de descripciones exactas (admite la coma). "
            "null, omitido o texto vacio = todos; texto de solo comas o lista sin nombres "
            f"([] incluida) = ninguno. La lista: hasta {TOPE_DE_INSUMOS} descripciones y "
            f"{TOPE_DE_CARACTERES} caracteres en total"
        ),
    )

    @field_validator("insumos")
    @classmethod
    def _total_de_caracteres(cls, valor: str | list[str] | None) -> str | list[str] | None:
        if isinstance(valor, list) and sum(len(i) for i in valor) > TOPE_DE_CARACTERES:
            raise ValueError(MENSAJE_TOPE_DE_CARACTERES)
        return valor


class FilaSimuladaRespuesta(BaseModel):
    tipo: str
    insumo: str
    unidad: str
    precio: str


class SimulacionRespuesta(BaseModel):
    filas: list[FilaSimuladaRespuesta]


def _filas(sesion: SesionDep, peticion: SimulacionPeticion):
    return simular_desde_catalogo(
        sesion, peticion.variacion_max, peticion.semilla, peticion.insumos
    )


@router.post("", response_model=SimulacionRespuesta, dependencies=EDITAR)
def simular_lista(sesion: SesionDep, peticion: SimulacionPeticion) -> SimulacionRespuesta:
    """Aplica variaciones deterministas a la lista vigente y devuelve las filas."""
    return SimulacionRespuesta(
        filas=[
            FilaSimuladaRespuesta(tipo=tipo, insumo=insumo, unidad=unidad or "", precio=str(precio))
            for tipo, insumo, unidad, precio in _filas(sesion, peticion)
        ]
    )


@router.post(
    "/csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
    dependencies=EDITAR,
)
def simular_lista_csv(sesion: SesionDep, peticion: SimulacionPeticion) -> Response:
    """La misma simulacion como CSV para descargar."""
    filas = _filas(sesion, peticion)
    if not filas:
        raise ValueError(MENSAJE_SIN_FILAS)
    return Response(
        content=csv_de(filas),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{NOMBRE_CSV}"'},
    )
