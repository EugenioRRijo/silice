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
`insumos` son descripciones separadas por coma (vacio o `null` = todos). Errores como en
Streamlit, en `{"detalle": ...}`: variacion no decimal o valores invalidos, 422; sin lista
vigente, 409. El acceso lo exige `api.main` con `exigir_clave_o_sesion(Accion.EDITAR_HOJA)`.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.dependencias import SesionDep
from aplicacion.simulador import (
    MENSAJE_SIN_FILAS,
    NOMBRE_CSV,
    csv_de,
    simular_desde_catalogo,
)

router = APIRouter(prefix="/v1/simulador", tags=["simulador"])

#: Tope de `int64`: lo que admite el campo numerico de la pagina Streamlit.
SEMILLA_MAXIMA = 2**63 - 1


class SimulacionPeticion(BaseModel):
    semilla: int = Field(42, ge=0, le=SEMILLA_MAXIMA, strict=True)
    variacion_max: str = Field("5", max_length=40, description="Porcentaje, decimal como texto")
    insumos: str | None = Field(
        None, max_length=20000, description="Separados por coma; vacio o null = todos"
    )


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


@router.post("", response_model=SimulacionRespuesta)
def simular_lista(sesion: SesionDep, peticion: SimulacionPeticion) -> SimulacionRespuesta:
    """Aplica variaciones deterministas a la lista vigente y devuelve las filas."""
    return SimulacionRespuesta(
        filas=[
            FilaSimuladaRespuesta(tipo=tipo, insumo=insumo, unidad=unidad or "", precio=str(precio))
            for tipo, insumo, unidad, precio in _filas(sesion, peticion)
        ]
    )


@router.post("/csv", response_class=Response, responses={200: {"content": {"text/csv": {}}}})
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
