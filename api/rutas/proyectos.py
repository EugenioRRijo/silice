"""`GET /v1/proyectos`: los proyectos del caso de la sesión (ola 0a de la sesión 2b).

`[{codigo, nombre, version_vigente, version_codigo, actualizado}]`, en orden alfabético, sobre
`aplicacion.proyectos.proyectos_del_caso` con la sesión del caso de la petición (RM-2):

- `codigo`: el identificador del proyecto en la base, como texto (el modelo no tiene otro código);
- `version_vigente`: el `id` de la versión vigente (el presupuesto de mayor `id` no descartado, la
  misma regla que la barra de Streamlit), o `null` sin versiones;
- `version_codigo`: el código de esa versión, el que muestra la barra (agregado al contrato del
  plan: el selector lo necesita para rotularla); `actualizado`: su fecha ISO, o `null`.

`LEER_PROYECTO` (arma y revisa), como la barra y el Tablero.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from api.acceso import LEER
from api.dependencias import SesionDep
from aplicacion.proyectos import proyectos_del_caso

router = APIRouter(prefix="/v1/proyectos", tags=["proyectos"])


class ProyectoDelCasoRespuesta(BaseModel):
    codigo: str
    nombre: str
    version_vigente: int | None
    version_codigo: str | None
    actualizado: str | None


@router.get("", response_model=list[ProyectoDelCasoRespuesta], dependencies=LEER)
def listar_proyectos_del_caso(sesion: SesionDep) -> list[ProyectoDelCasoRespuesta]:
    """Los proyectos del caso de esta sesión con su versión vigente."""
    return [
        ProyectoDelCasoRespuesta(
            codigo=str(fila.id),
            nombre=fila.nombre,
            version_vigente=fila.version_id,
            version_codigo=fila.version_codigo,
            actualizado=None if fila.version_fecha is None else fila.version_fecha.isoformat(),
        )
        for fila in proyectos_del_caso(sesion)
    ]
