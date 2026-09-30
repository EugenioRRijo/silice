"""API FastAPI que expone las operaciones del nucleo (Sesion F.1)."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.rutas import catalogo, computos, listas, presupuestos, rendimientos
from core.catalog import CatalogoIncompleto

DESCRIPCION = """API HTTP sobre el nucleo del sistema de Analisis de Precios Unitarios (APU).

**Los montos viajan como texto, nunca como numero JSON.** Todo campo monetario o dimensional
(precios, cantidades, factores, totales) se serializa como `str` en formato decimal
(por ejemplo `"1586.61"`) tanto en las peticiones como en las respuestas; la conversion a
`Decimal` ocurre siempre en la frontera de la API, construyendo desde el texto exacto. Esto evita
la perdida de precision de `float` en JSON (regla 3 de NORMAS.md).
"""

app = FastAPI(title="Sistema APU multidominio", version="0.1.0", description=DESCRIPCION)
app.include_router(catalogo.router)
app.include_router(listas.router)
app.include_router(computos.router)
app.include_router(presupuestos.router)
app.include_router(rendimientos.router)


@app.exception_handler(CatalogoIncompleto)
def manejar_catalogo_incompleto(_request: Request, exc: CatalogoIncompleto) -> JSONResponse:
    """Falta un dato imprescindible en el catalogo (precio o rendimiento vigente)."""
    return JSONResponse(status_code=409, content={"detalle": str(exc)})


@app.exception_handler(HTTPException)
def manejar_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
    """Un conflicto o error explicito de una ruta (ej. codigo de presupuesto ambiguo entre
    proyectos, o UC-02 sin nada que confirmar): mismo formato `{"detalle": ...}` que el resto de
    la API, en vez del `{"detail": ...}` que usa FastAPI por defecto.
    """
    return JSONResponse(status_code=exc.status_code, content={"detalle": exc.detail})


@app.exception_handler(LookupError)
def manejar_lookup_error(_request: Request, exc: LookupError) -> JSONResponse:
    """El recurso pedido (partida, insumo...) no existe en el catalogo."""
    return JSONResponse(status_code=404, content={"detalle": str(exc)})


@app.exception_handler(ValueError)
def manejar_value_error(_request: Request, exc: ValueError) -> JSONResponse:
    """Datos de entrada invalidos segun las reglas del nucleo."""
    return JSONResponse(status_code=422, content={"detalle": str(exc)})
