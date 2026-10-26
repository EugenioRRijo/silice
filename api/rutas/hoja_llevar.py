"""`POST /v1/hoja/llevar`: Elaborar lleva sus ítems a la Hoja de la obra (Tarea 12 del plan de
montar un presupuesto, `docs/planes/PLAN_MONTAR_PRESUPUESTO.md`; diseño §5.3: «Llevar a la Hoja
del proyecto», que mete sus ítems en el borrador como renglones agregados, sin guardar por su
cuenta).

Cuerpo `{proyecto, partidas: [{codigo, cantidad, calculo}]}` → 200 `{borrador_id}`. Usa el borrador
vivo de esa ficha y obra o abre uno sobre la versión vigente (o en blanco) y agrega cada partida con
`hoja_edicion.agregar` (Tarea 9), todo o nada (`aplicacion.elaboracion.llevar_a_la_hoja`); no guarda
versión. `proyecto` es el código de `GET /v1/proyectos` o el nombre de la obra.

La cantidad es texto de máquina: la que da el cómputo de Elaborar, con punto decimal y sin miles,
como en `POST /presupuestos/calcular` (bitácora de la coma decimal: las rutas cuyo contrato ya es un
decimal con punto no cambian). El servidor la escribe con coma antes de agregarla, así «1.125» es
uno coma ciento veinticinco. `calculo` (opcional) es el de la Tarea 8, con coma decimal.

Como el resto de la Hoja: solo con una cuenta con `editar_hoja` (la clave de API, 403), CSRF y
`Origin` propios, `Cache-Control: no-store` también en los errores y un 422 de forma que no repite
lo enviado. Errores: obra que no existe, 404 sin eco; partida fuera del catálogo, 404 (Tarea 9);
cálculo o cifra, 422 con el código de la partida delante; sin lista para valorar la obra o versión
vigente que ya no se abre, 409; la base, 503.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import SesionDep, url_de_la_peticion
from api.esquemas_ola2 import MAX_ITEMS
from api.rutas.hoja import MENSAJE_BASE, CuentaDeLaHoja
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import elaboracion, hoja_edicion
from aplicacion.entrega import con_anexos_de_cadena
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorInexistente, RevDesactualizado
from aplicacion.proyectos import resolver_proyecto

FORMA_LLEVAR = (
    f"Lo que se lleva a la Hoja no tiene la forma esperada: envíe la obra y de 1 a {MAX_ITEMS} "
    "partidas, cada una con su código y su cantidad tal como salen del cómputo."
)
MENSAJE_CAMBIO = (
    "El borrador de la obra cambió mientras se llevaban las partidas: no se llevó ninguna. "
    "Vuelva a intentarlo."
)


class _RutaLlevar(RutaSinCache, RutaSinEco):
    """Como `_RutaHoja`: `RutaSinCache` envuelve a `RutaSinEco` (si no, el 422 tendría eco)."""

    mensaje_por_omision = FORMA_LLEVAR


router = APIRouter(prefix="/v1/hoja", tags=["hoja"], route_class=_RutaLlevar)


class PartidaLlevada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    #: Decimal con punto y sin miles, sin signo ni exponente: el texto del cómputo.
    cantidad: Annotated[str, Field(strict=True, max_length=500, pattern=r"^[0-9]+(\.[0-9]+)?$")]
    calculo: Annotated[str, Field(strict=True, max_length=500)] = ""


class LlevarALaHoja(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proyecto: Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    partidas: Annotated[list[PartidaLlevada], Field(min_length=1, max_length=MAX_ITEMS)]


class LlevadoRespuesta(BaseModel):
    """El borrador de la obra con las partidas ya agregadas (sin guardar)."""

    borrador_id: str


def _hoy() -> date:
    """El día del borrador en blanco y de la evaluación de precios: hoy (las pruebas lo fijan)."""
    return date.today()


@router.post("/llevar", response_model=LlevadoRespuesta)
@sin_eco(FORMA_LLEVAR)
def llevar_a_la_hoja(
    datos: LlevarALaHoja, request: Request, activa: CuentaDeLaHoja, sesion: SesionDep
) -> LlevadoRespuesta:
    """Lleva las partidas al borrador de la Hoja de la obra, todo o nada, sin guardar versión.

    `activa` va antes que `sesion`: el acceso (401, 403) responde antes de abrir la base del caso.
    Abrir la versión vigente escribe su instantánea si faltaba (UC-15e), como abrir la Hoja."""
    partidas = [
        elaboracion.PartidaParaLlevar(p.codigo.strip(), Decimal(p.cantidad), p.calculo)
        for p in datos.partidas
    ]
    try:
        con_anexos_de_cadena(sesion)  # el sello de lo que se escriba cubre los anexos (§1.2)
        proyecto = resolver_proyecto(sesion, datos.proyecto)
        if proyecto is None:
            raise HTTPException(status_code=404, detail=elaboracion.MENSAJE_SIN_OBRA)
        borrador_id = elaboracion.llevar_a_la_hoja(
            sesion,
            activa.huella_ficha,
            url_de_la_peticion(request),
            proyecto,
            partidas,
            responsable=activa.usuario,
            hoy=_hoy(),
        )
    except hoja_edicion.PartidaFueraDelCatalogo as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (hoja_edicion.SinListaDeLaObra, elaboracion.VersionQueNoSeAbre) as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except (
        hoja_edicion.BorradorYaGuardado,
        RevDesactualizado,
        BorradorInexistente,
    ):
        raise HTTPException(status_code=409, detail=MENSAJE_CAMBIO) from None
    except HojaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return LlevadoRespuesta(borrador_id=borrador_id)
