"""`/v1/riesgo`: el riesgo de la obra y el informe de mejora de la estimación (plan vial, fase C).

Por ahora una sola ruta (Tarea 15); la Tarea 16 suma la proyección y la comprobación hacia atrás.

- `POST /mejora` `{costo_final_real, presupuesto_original, estimacion_silice}` → 200
  `{error_original_pct, error_silice_pct, mejora_pp}`, todo texto con punto decimal. Cálculo puro
  (`aplicacion.riesgo.mejora`): no toca la base ni la carpeta abierta.

Acceso: `Accion.VER_RIESGO` (arma, revisa y administrador), con clave de API o sesión web (cookie
más `X-Silice-CSRF` y `Origin`, porque el método escribe). Las cifras entran como **texto con punto
decimal**, igual que en el resto de la API (la coma es cosa del front, `cifraEscrita.ts`); un texto
que no es decimal, un costo real que no es positivo o una estimación negativa es 422 con
`{"detalle": ...}`.
"""

from __future__ import annotations

import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StrictStr

from api.sesion_web import exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from aplicacion.riesgo.mejora import mejora_de_estimacion
from seguridad.permisos import Accion

VER_RIESGO = exigir_clave_o_sesion(Accion.VER_RIESGO)

router = APIRouter(
    prefix="/v1/riesgo",
    tags=["riesgo"],
    dependencies=[Depends(VER_RIESGO)],
    route_class=RutaSinCache,
)

__all__ = ["VER_RIESGO", "router"]

#: Un decimal con punto, sin exponente, NaN ni infinito (lo mismo que el resto de la API).
_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


class MejoraEntrada(BaseModel):
    costo_final_real: StrictStr  # decimal con punto
    presupuesto_original: StrictStr  # decimal con punto
    estimacion_silice: StrictStr  # decimal con punto


class MejoraRespuesta(BaseModel):
    error_original_pct: str  # dos decimales, con punto
    error_silice_pct: str
    mejora_pp: str  # negativa si Sílice acertó menos que el original


def _decimal(nombre: str, texto: str) -> Decimal:
    if not _DECIMAL.fullmatch(texto.strip()):
        raise HTTPException(
            status_code=422,
            detail=f"{nombre}: escriba un número decimal con punto, por ejemplo 1250.50.",
        )
    return Decimal(texto.strip())


@router.post("/mejora", response_model=MejoraRespuesta)
def informe_de_mejora(cuerpo: MejoraEntrada) -> MejoraRespuesta:
    real = _decimal("costo_final_real", cuerpo.costo_final_real)
    original = _decimal("presupuesto_original", cuerpo.presupuesto_original)
    silice = _decimal("estimacion_silice", cuerpo.estimacion_silice)
    try:
        mejora = mejora_de_estimacion(real, original, silice)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return MejoraRespuesta(
        error_original_pct=str(mejora.error_original_pct),
        error_silice_pct=str(mejora.error_silice_pct),
        mejora_pp=str(mejora.mejora_pp),
    )
