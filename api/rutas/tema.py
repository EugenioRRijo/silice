"""`GET /v1/tema` y `GET /v1/tema/logo`: el tema de la empresa (rediseño del marco, Tarea 1).

Públicas (sin clave ni sesión): la pantalla de entrada se pinta con ellas antes de que haya
cuenta. Solo dicen tres colores y si hay un logo; nunca rutas ni nombres. La carpeta es
`<datos>/tema/`, la misma raíz de datos que `instalacion.db`. La lógica vive en `aplicacion.tema`;
cualquier archivo roto cae al tema neutro sin dar error.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from aplicacion import tema
from operacion import config

router = APIRouter(tags=["tema"])


class TemaRespuesta(BaseModel):
    acento: str | None
    marco: str | None
    lateral: str | None
    tiene_logo: bool


def _carpeta():
    return config.carpeta_datos() / tema.NOMBRE_CARPETA


@router.get("/v1/tema", response_model=TemaRespuesta)
def ver_tema() -> TemaRespuesta:
    """Colores válidos (`#rrggbb`) y si hay logo; lo demás, `null` (tema neutro)."""
    leido = tema.leer_tema(_carpeta())
    return TemaRespuesta(
        acento=leido.acento,
        marco=leido.marco,
        lateral=leido.lateral,
        tiene_logo=leido.tiene_logo,
    )


@router.get("/v1/tema/logo", response_class=Response, responses={200: {"content": {"image/*": {}}}})
def ver_logo() -> Response:
    """El logo (PNG, JPEG o WebP de hasta 512 KB) o 404."""
    encontrado = tema.logo_de(_carpeta())
    if encontrado is None:
        raise HTTPException(status_code=404, detail="No hay logo.")
    archivo, tipo = encontrado
    try:
        contenido = archivo.read_bytes()
    except OSError:
        raise HTTPException(status_code=404, detail="No hay logo.") from None
    return Response(
        content=contenido,
        media_type=tipo,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-cache"},
    )
