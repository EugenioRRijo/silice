"""`GET /v1/proyectos`: los proyectos del caso de la sesión (ola 0a de la sesión 2b).

`[{codigo, nombre, version_vigente, version_codigo, actualizado}]`, en orden alfabético, sobre
`aplicacion.proyectos.proyectos_del_caso` con la sesión del caso de la petición (RM-2):

- `codigo`: el identificador del proyecto en la base, como texto (el modelo no tiene otro código);
- `version_vigente`: el `id` de la versión vigente (el presupuesto de mayor `id` no descartado, la
  misma regla que la barra de Streamlit), o `null` sin versiones;
- `version_codigo`: el código de esa versión, el que muestra la barra (agregado al contrato del
  plan: el selector lo necesita para rotularla); `actualizado`: su fecha ISO, o `null`.

`LEER_PROYECTO` (arma y revisa), como la barra y el Tablero.

`POST /v1/proyectos` (BCP-3, diseño `2026-10-21-bienvenida-casos-proyectos-design.md` §5): crea un
proyecto en el caso de la petición (el de la ficha, RM-2) con `EDITAR_HOJA` (clave de API o sesión).
`{nombre ≤ 120, moneda: "Bs"|"USD"|null, dominio: ""|civil|telecom|industrial|sistemas,
descripcion ≤ 500, cliente ≤ 200, ubicacion ≤ 200}` → 201 con la forma de un elemento de la lista
(`version_vigente: null`). MOD-3a: `cliente` y `ubicacion` (vacíos por omisión) son la ficha de la
obra (`aplicacion.obras`), guardada en la misma transacción que el proyecto; `GET` los repite. El
responsable de la moneda es la cuenta de la sesión (`Nombre <login>`, RF-82) o, con clave de API,
`USUARIO_API`. Va sobre la sesión de escritura (`BEGIN IMMEDIATE`): dos peticiones con el mismo
nombre dan 201 y 409. Errores: 409 repetido; 422 vacío, moneda o tipo de obra (textos con tilde,
DV-BCP-3). El 422 de forma no repite lo enviado (`RutaSinEco`).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.acceso import LEER
from api.dependencias import USUARIO_API, SesionDeEscrituraDep, SesionDep
from api.sesion_web import exigir_clave_o_sesion
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import obras
from aplicacion.proyectos import (
    ProyectoInvalido,
    ProyectoRepetido,
    crear_proyecto_en_sesion,
    proyectos_del_caso,
)
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Indique el nombre de la obra (hasta 120 caracteres), la moneda (Bs o USD), el tipo de obra "
    "y una descripción de hasta 500 caracteres."
)


class _RutaProyectos(RutaSinEco):
    mensaje_por_omision = MENSAJE_CUERPO_INVALIDO


router = APIRouter(prefix="/v1/proyectos", tags=["proyectos"], route_class=_RutaProyectos)
EDITAR_HOJA = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))


class ProyectoDelCasoRespuesta(BaseModel):
    codigo: str
    nombre: str
    version_vigente: int | None
    version_codigo: str | None
    actualizado: str | None
    cliente: str = ""
    ubicacion: str = ""


@router.get("", response_model=list[ProyectoDelCasoRespuesta], dependencies=LEER)
def listar_proyectos_del_caso(sesion: SesionDep) -> list[ProyectoDelCasoRespuesta]:
    """Los proyectos del caso de esta sesión con su versión vigente."""
    guardadas = obras.fichas(sesion)
    return [
        ProyectoDelCasoRespuesta(
            codigo=str(fila.id),
            nombre=fila.nombre,
            version_vigente=fila.version_id,
            version_codigo=fila.version_codigo,
            actualizado=None if fila.version_fecha is None else fila.version_fecha.isoformat(),
            cliente=guardadas.get(fila.id, obras.SIN_FICHA).cliente,
            ubicacion=guardadas.get(fila.id, obras.SIN_FICHA).ubicacion,
        )
        for fila in proyectos_del_caso(sesion)
    ]


class ProyectoNuevo(BaseModel):
    nombre: str = Field(max_length=120)
    moneda: str | None = None
    dominio: str = ""
    descripcion: str = Field(default="", max_length=500)
    cliente: str = Field(default="", max_length=200)
    ubicacion: str = Field(default="", max_length=200)


@router.post(
    "", response_model=ProyectoDelCasoRespuesta, status_code=201, dependencies=[EDITAR_HOJA]
)
@sin_eco(MENSAJE_CUERPO_INVALIDO)
def crear_proyecto_del_caso(
    sesion: SesionDeEscrituraDep,
    peticion: ProyectoNuevo,
    activa: Annotated[SesionActiva | None, EDITAR_HOJA],
) -> ProyectoDelCasoRespuesta:
    """Crea el proyecto en el caso de esta sesión; sin versión guardada todavía."""
    responsable = USUARIO_API if activa is None else activa.usuario
    ficha = obras.FichaObra(peticion.cliente, peticion.ubicacion)
    try:
        proyecto = crear_proyecto_en_sesion(
            sesion,
            peticion.nombre,
            peticion.moneda,
            peticion.dominio,
            peticion.descripcion,
            responsable,
            # la función se busca al llamar: ficha y proyecto se confirman juntos o ninguno
            lambda abierta, nuevo: obras.guardar_ficha(abierta, nuevo.id, ficha),
        )
    except ProyectoRepetido as error:
        raise HTTPException(409, str(error)) from None
    except ProyectoInvalido as error:
        raise HTTPException(422, str(error)) from None
    return ProyectoDelCasoRespuesta(
        codigo=str(proyecto.id),
        nombre=proyecto.nombre,
        version_vigente=None,
        version_codigo=None,
        actualizado=None,
        cliente=peticion.cliente,
        ubicacion=peticion.ubicacion,
    )
