"""`GET /v1/libros/que-hacer`: el «Qué hacer» de cada hallazgo y alerta de precio de un libro.

B2, ficha-b2 §3.3. Es una capa de presentación **aparte** de `api/rutas/libros.py` (sellado por la
etiqueta `reglas-congeladas-2026-11-24`): no recibe el libro ni lo guarda, y devuelve el catálogo de
`aplicacion/que_hacer.py` (la guía de cada código de regla, de cada tipo de alerta y la genérica).
La pantalla de auditoría junta esta respuesta con la de `POST /v1/libros/auditoria` por código de
regla y por tipo de alerta.

Mismo acceso que las demás rutas de libros (clave de API o sesión con `leer_proyecto`; lo exige
`api.main`).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from api.sin_cache import RutaSinCache
from aplicacion.que_hacer import catalogo

router = APIRouter(prefix="/v1/libros", tags=["libros"], route_class=RutaSinCache)


@router.get("/que-hacer")
def que_hacer_de_los_hallazgos() -> dict[str, Any]:
    """La guía por código de regla (`reglas`), por tipo de alerta (`alertas`) y la genérica."""
    return catalogo()
