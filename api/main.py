"""API FastAPI que expone las operaciones del nucleo (Sesion F.1).

Acceso (RM-3, sesion 2b): cada ruta lleva en su decorador la clave de API o la sesion del navegador
con la accion de su pagina Streamlit; la tabla ruta -> accion esta en `api/acceso.py`. Aqui los
routers se incluyen sin dependencias propias, salvo los de libros (RS2-5).
"""

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api import interfaz
from api.proteccion import opciones_documentacion, proteger
from api.rutas import (
    acerca,
    admin_claves_api,
    admin_empresa,
    admin_instalacion,
    auditorias,
    casos,
    catalogo,
    composicion,
    computos,
    entregas,
    libros,
    listas,
    presupuestos,
    proyectos,
    rendimientos,
    sesion,
    similares,
    simulador,
)
from api.sesion_web import exigir_clave_o_sesion
from core.catalog import CatalogoIncompleto
from operacion.version import version
from seguridad.permisos import Accion

LEER_PROYECTO = Accion.LEER_PROYECTO  # arma o revisa (RS2-5)

DESCRIPCION = """API HTTP sobre el nucleo del sistema de Analisis de Precios Unitarios (APU).

**Los montos viajan como texto, nunca como numero JSON.** Todo campo monetario o dimensional
(precios, cantidades, factores, totales) se serializa como `str` en formato decimal
(por ejemplo `"1586.61"`) tanto en las peticiones como en las respuestas; la conversion a
`Decimal` ocurre siempre en la frontera de la API, construyendo desde el texto exacto. Esto evita
la perdida de precision de `float` en JSON (regla 3 de NORMAS.md).
"""

app = FastAPI(
    title="Sílice", version=version(), description=DESCRIPCION, **opciones_documentacion()
)
# RF-98: clave (o, desde la ola 0a, sesion) en todas las rutas salvo /salud. El `CON_CLAVE` por
# router se retiro (RM-3): cada ruta declara `exigir_clave_o_sesion(<accion>)` (`api/acceso.py`),
# que con `X-Silice-Clave` es `exigir_clave_api`.
app.include_router(catalogo.router)
app.include_router(listas.router)
app.include_router(computos.router)
app.include_router(presupuestos.router)
app.include_router(rendimientos.router)
app.include_router(auditorias.router)  # S3 §10: POST /v1/auditorias
# 1.5: /v1/libros (auditoria, devolucion y pdf); 1.2.0: replica, y clave o sesión (RS2-5)
app.include_router(libros.router, dependencies=[Depends(exigir_clave_o_sesion(LEER_PROYECTO))])
# Migracion: el simulador de listas (no escribe en la base); clave o sesion con EDITAR_HOJA
app.include_router(
    simulador.router, dependencies=[Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))]
)
# 1.2.0 (RT-9): acceso del navegador por cuenta y cookie; sin clave de API a propósito
app.include_router(sesion.router)
# Ola 1 (sesion 2b): GET /v1/acerca, con la clave de API o la sesion de cualquier rol
app.include_router(acerca.router)
# 2b: «Partidas similares» de la interfaz nueva (UC-03); clave o sesión con editar_hoja
app.include_router(
    similares.router, dependencies=[Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))]
)
# Ola 0a (sesion 2b): el caso de la sesion web (RM-2) y los proyectos del caso
app.include_router(casos.router)
app.include_router(proyectos.router)
# Ola 3 (S2-B): «Componer una partida» (UC-10, UC-11)
app.include_router(composicion.router)
# Ola 4 (sesion 2b): entregar el paquete auditado
app.include_router(entregas.router)
# 1.2.0 (RT-2): la interfaz nueva, estática y sin secretos, en /app con CSP
# Ola 5 (sesion 2b): Administracion (empresa y firma, claves de API, instalacion); solo con sesion
app.include_router(admin_empresa.router)
app.include_router(admin_claves_api.router)
app.include_router(admin_instalacion.router)
interfaz.montar(app)


@app.get("/salud", tags=["catalogo"])
def salud() -> dict[str, str]:
    """Ping de disponibilidad, sin clave, sin versión y sin tocar la base (spec S5 §8.3)."""
    return {"estado": "ok"}


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
    # Las cabeceras de la excepcion (p. ej. `Retry-After` del 429) viajan con la respuesta.
    return JSONResponse(
        status_code=exc.status_code, content={"detalle": exc.detail}, headers=exc.headers
    )


@app.exception_handler(LookupError)
def manejar_lookup_error(_request: Request, exc: LookupError) -> JSONResponse:
    """El recurso pedido (partida, insumo...) no existe en el catalogo."""
    return JSONResponse(status_code=404, content={"detalle": str(exc)})


@app.exception_handler(ValueError)
def manejar_value_error(_request: Request, exc: ValueError) -> JSONResponse:
    """Datos de entrada invalidos segun las reglas del nucleo."""
    return JSONResponse(status_code=422, content={"detalle": str(exc)})


proteger(app)  # al final: ya están todas las rutas y los filtros envuelven la aplicación
