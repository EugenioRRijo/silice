"""Las rutas de `QUE_ESCRIBEN` abren `BEGIN IMMEDIATE`.

Desde el anexo A.8 del plan de desenredo (2026-11-18) toda ruta no-GET que sigue con la sesion
comun esta clasificada a mano: o no confirma nada en el caso (`SOLO_LEEN_EL_CASO`) o confirma y se
queda con la sesion comun por una razon escrita (`ESCRIBEN_CON_LA_SESION_COMUN`). Una ruta nueva
que no este en ninguna de las dos hace fallar
`test_toda_ruta_no_get_con_la_sesion_comun_esta_clasificada`: o pasa a `SesionDeEscrituraDep` (y a
`QUE_ESCRIBEN`) o se clasifica.

Con la sesion comun (`sesion_api`, `BEGIN` diferido) la transaccion empieza leyendo: si entre esa
lectura y la primera escritura otra peticion escribe y confirma, SQLite no puede ascender la
lectura a escritura sobre una instantanea vieja y responde `database is locked` en el acto, sin
esperar el `busy_timeout`. Con `sesion_de_escritura_api` quien escribe toma el bloqueo antes de
leer y el otro espera (`api/dependencias.py`, SL-E12). Se mira lo que FastAPI inyecta de verdad
(el arbol de dependencias de cada ruta), no el texto de la firma.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant
from fastapi.routing import APIRoute

from api.dependencias import SesionDeEscrituraDep, SesionDep, sesion_api, sesion_de_escritura_api
from api.main import app

#: (metodo, ruta) de cada ruta que guarda una version, un proyecto, un presupuesto, un rendimiento,
#: una ejecucion o un dato del control de obra.
QUE_ESCRIBEN = [
    ("POST", "/proyectos"),
    ("POST", "/presupuestos"),
    ("POST", "/presupuestos/importar"),
    ("POST", "/presupuestos/{codigo}/actualizacion"),
    ("POST", "/presupuestos/revalorar"),
    ("POST", "/presupuestos/{codigo}/descartar"),
    ("POST", "/v1/control/recuperacion/elegir"),
    # Anexo A.3 del plan de desenredo (H8, DS-2): las demas escrituras con BEGIN diferido.
    ("POST", "/presupuestos/calcular/declarar-rendimiento"),
    ("POST", "/ejecuciones"),
    ("POST", "/partidas/{codigo}/rendimientos"),
    ("POST", "/v1/control/linea-base"),
    ("POST", "/v1/control/parametros"),
    ("POST", "/v1/control/valuaciones"),
    ("POST", "/v1/control/valuaciones/{valuacion_id}/anular"),
    ("POST", "/v1/control/costos"),
    ("POST", "/v1/control/importar"),
    # Anexo A.8 (2026-11-18): las demas que confirman en el caso.
    ("POST", "/listas-precios"),
    ("POST", "/v1/composicion/guardar"),
    ("POST", "/v1/reajuste/guardar"),
    ("POST", "/v1/indices/confirmar"),
    ("POST", "/v1/indices/en-usd/confirmar"),
    ("POST", "/v1/indices/series-viales/importar"),
    ("POST", "/v1/precios-empresa/listas"),
    ("POST", "/v1/precios-empresa/referencia"),
    ("PUT", "/v1/vial/tramos"),
    ("POST", "/v1/vial/tramos/importar"),
    ("POST", "/v1/produccion/calculos/{calculo_id}/publicar"),
    ("POST", "/v1/revision/dictamen"),
    # Tarea A.9 (DS-49, DS-53): el cerrojo del borrador antes del bloqueo de escritura.
    ("POST", "/v1/hoja/libro"),
    # Mejora de la DS-81 (DS-91): el mapa de series que recuerda Riesgo, en una ruta aparte de la
    # proyeccion para no retener el bloqueo de escritura durante el Monte Carlo.
    ("PUT", "/v1/riesgo/mapa"),
]

_BORRADOR = "/v1/hoja/borradores/{id}"
_EDITA_EL_BORRADOR = "edita el borrador vivo, en memoria del proceso; el caso solo se lee"

#: DS-51: no confirman, pero escriben y deshacen. Con el BEGIN diferido toman el bloqueo de
#: escritura desde el primer flush hasta cerrar la sesion (cerrarla antes de responder va con A.9).
_DESHACE = (
    "escribe y deshace: con el BEGIN diferido toma el bloqueo de escritura desde el flush hasta "
    "cerrar la sesion (DS-51)"
)

#: Rutas no-GET con la sesion comun que no confirman nada en el caso (revisadas una a una el
#: 2026-11-18, anexo A.8; como se comprobo, en el acta DS-45).
SOLO_LEEN_EL_CASO: dict[tuple[str, str], str] = {
    ("POST", "/listas-precios/vista-previa"): "UC-02 2a: los desconocidos del archivo",
    ("POST", "/presupuestos/calcular"): "calcula sin guardar; la lista convertida " + _DESHACE,
    ("POST", "/presupuestos/calcular/excel"): "el mismo calculo, en Excel; " + _DESHACE,
    ("POST", "/presupuestos/{codigo}/escenarios"): "escenarios en memoria",
    ("POST", "/presupuestos/{codigo}/escenarios/csv"): "los mismos escenarios, en CSV",
    ("POST", "/v1/auditorias"): "audita el documento enviado",
    ("POST", "/v1/libros/auditoria"): "guarda el resultado en instalacion.db, no en el caso",
    ("POST", "/v1/libros/devolucion"): "devuelve el libro anotado",
    ("POST", "/v1/libros/auditoria/pdf"): "el informe de la auditoria en PDF; no guarda nada",
    ("POST", "/v1/simulador"): "simula sobre la lista, en memoria",
    ("POST", "/v1/simulador/csv"): "la misma simulacion, en CSV",
    ("POST", "/v1/similares"): "propone partidas parecidas",
    ("POST", "/v1/composicion/evaluar"): "el desglose en vivo",
    ("POST", "/v1/composicion/prever"): "lo que haria el guardado; " + _DESHACE,
    ("POST", "/v1/control/recuperacion/opciones"): "las opciones de recuperacion (DS-29)",
    ("POST", "/v1/entregas"): "el paquete sale en memoria; el rastro va a instalacion.db",
    ("POST", "/v1/reajuste/calcular"): "calcula el reajuste sin guardarlo; " + _DESHACE,
    ("POST", "/v1/reajuste/excel"): "el mismo reajuste, en Excel",
    ("POST", "/v1/indices/en-usd/ver"): "la serie en USD antes de confirmarla",
    ("POST", "/v1/precios-empresa/listas/revision"): "revisa el archivo antes de crear la lista",
    ("POST", "/v1/riesgo/proyeccion"): "proyeccion de la obra",
    ("POST", "/v1/riesgo/comprobacion"): "comprobacion de la obra",
    ("POST", "/v1/produccion/calculos"): "el calculo se registra en instalacion.db",
    ("POST", f"{_BORRADOR}/partidas"): _EDITA_EL_BORRADOR,
    ("POST", f"{_BORRADOR}/partidas/quitar"): _EDITA_EL_BORRADOR,
    ("PUT", f"{_BORRADOR}/espacio"): _EDITA_EL_BORRADOR,
    ("PUT", f"{_BORRADOR}/cantidades"): _EDITA_EL_BORRADOR,
    ("PUT", f"{_BORRADOR}/parametros"): _EDITA_EL_BORRADOR,
    ("PUT", f"{_BORRADOR}/plan"): _EDITA_EL_BORRADOR,
    ("POST", f"{_BORRADOR}/plan/secuencial"): _EDITA_EL_BORRADOR,
    ("POST", f"{_BORRADOR}/plan/rendimientos"): _EDITA_EL_BORRADOR,
    ("PUT", f"{_BORRADOR}/apu/{{partida:path}}"): _EDITA_EL_BORRADOR,
    ("POST", f"{_BORRADOR}/apu/{{partida:path}}/insumo"): _EDITA_EL_BORRADOR,
    ("POST", f"{_BORRADOR}/apu/{{partida:path}}/lineas"): _EDITA_EL_BORRADOR,
    ("POST", f"{_BORRADOR}/apu/{{partida:path}}/lineas/quitar"): _EDITA_EL_BORRADOR,
    ("PUT", f"{_BORRADOR}/frentes"): _EDITA_EL_BORRADOR,
    ("POST", f"{_BORRADOR}/plano/fusionar"): _EDITA_EL_BORRADOR,
}

_INSTANTANEA = (
    "abrir la version escribe su instantanea si faltaba (UC-15e, `hoja.abrir_version`); con "
    "BEGIN IMMEDIATE el bloqueo de escritura duraria todo el armado del borrador (DS-44)"
)
_RECIBIDO = (
    "registra el paquete una vez por SHA-256 y ya atrapa la carrera de la UNIQUE; con BEGIN "
    "IMMEDIATE las lecturas tras ese commit (reauditoria, contraste) tomarian el bloqueo hasta "
    "el final de la peticion (DS-44)"
)

#: Rutas que confirman en el caso y siguen con la sesion comun (2026-11-18, DS-44). Solo se
#: achica: una fila sale cuando su ruta pasa a `SesionDeEscrituraDep`.
ESCRIBEN_CON_LA_SESION_COMUN: dict[tuple[str, str], str] = {
    ("POST", "/v1/hoja/borradores"): _INSTANTANEA + "; quien solo lee la abre `sin_escribir`",
    ("POST", "/v1/hoja/llevar"): _INSTANTANEA,
    ("POST", "/v1/vial/tramos/llevar"): _INSTANTANEA,
    ("POST", "/v1/revision/paquete"): _RECIBIDO,
    ("POST", "/v1/revision/contra-lista"): _RECIBIDO,
    ("POST", "/v1/revision/excel"): _RECIBIDO,
}


def _rutas(router) -> Iterator[APIRoute]:
    """Como en `test_api_acceso_por_ruta.py`: FastAPI >= 0.140 no aplana `include_router`."""
    for ruta in router.routes:
        if isinstance(ruta, APIRoute):
            yield ruta
        elif hasattr(ruta, "original_router"):
            yield from _rutas(ruta.original_router)


def _rutas_completas(
    router, prefijo: str = "", de_la_inclusion: frozenset = frozenset()
) -> Iterator[tuple[str, APIRoute, frozenset]]:
    """(camino completo, ruta, dependencias puestas al incluir) bajando por cada
    `_IncludedRouter` de FastAPI 0.141: su `include_context` lleva el prefijo y las dependencias
    del `include_router`, que la ruta original no ve en su `path` ni en su `dependant`. De cada
    dependencia puesta al incluir se baja tambien a sus subdependencias (DS-50)."""
    for ruta in router.routes:
        if isinstance(ruta, APIRoute):
            yield prefijo + ruta.path, ruta, de_la_inclusion
        elif hasattr(ruta, "original_router"):
            contexto = ruta.include_context
            puestas = frozenset(
                llamada
                for d in contexto.dependencies
                if d.dependency is not None
                for llamada in (d.dependency, *_llamadas(get_dependant(path="", call=d.dependency)))
            )
            yield from _rutas_completas(
                ruta.original_router, prefijo + contexto.prefix, de_la_inclusion | puestas
            )


def _no_get_con_la_sesion_comun(router) -> set[tuple[str, str]]:
    """(metodo, camino) de cada ruta que no es GET y recibe `sesion_api`, en su firma o desde el
    `include_router` que la monta."""
    return {
        (metodo, camino)
        for camino, ruta, puestas in _rutas_completas(router)
        if sesion_api in set(_llamadas(ruta.dependant)) | puestas
        for metodo in ruta.methods - {"GET", "HEAD"}
    }


def _ruta(metodo: str, camino: str) -> APIRoute:
    halladas = [r for r in _rutas(app.router) if r.path == camino and metodo in r.methods]
    assert len(halladas) == 1, (metodo, camino, halladas)
    return halladas[0]


def _llamadas(dependiente: Dependant) -> Iterator[Callable[..., Any]]:
    for hija in dependiente.dependencies:
        if hija.call is not None:
            yield hija.call
        yield from _llamadas(hija)


@pytest.mark.parametrize(("metodo", "camino"), QUE_ESCRIBEN)
def test_la_ruta_que_escribe_usa_la_sesion_de_escritura(metodo: str, camino: str) -> None:
    llamadas = set(_llamadas(_ruta(metodo, camino).dependant))
    assert sesion_de_escritura_api in llamadas
    assert sesion_api not in llamadas


def test_la_guardia_distingue_las_dos_sesiones() -> None:
    """No pasa en vacio: una ruta que solo lee sigue con la sesion comun."""
    llamadas = set(_llamadas(_ruta("GET", "/presupuestos").dependant))
    assert sesion_api in llamadas and sesion_de_escritura_api not in llamadas


def test_toda_ruta_no_get_con_la_sesion_comun_esta_clasificada() -> None:
    """Anexo A.8: una ruta que confirma en el caso con `BEGIN` diferido puede perder la carrera
    contra otra que escribe (`database is locked` en el acto). La que no esta en ninguna lista
    pasa a `SesionDeEscrituraDep` o se clasifica con su razon.

    No ve: si la ruta confirma de verdad (eso lo dice la clasificacion a mano, DS-45), ni la sesion
    que se abre en el cuerpo de la ruta sin pasar por `Depends` (DS-50)."""
    sin_clasificar = (
        _no_get_con_la_sesion_comun(app.router)
        - set(SOLO_LEEN_EL_CASO)
        - set(ESCRIBEN_CON_LA_SESION_COMUN)
    )
    assert sorted(sin_clasificar) == []


def test_toda_ruta_no_get_con_la_sesion_comun_esta_clasificada_sin_sobrantes() -> None:
    """Las dos listas solo se achican: la fila cuya ruta ya no existe o ya no usa la sesion
    comun se borra."""
    hoy = _no_get_con_la_sesion_comun(app.router)
    sobrantes = (set(SOLO_LEEN_EL_CASO) | set(ESCRIBEN_CON_LA_SESION_COMUN)) - hoy
    assert sorted(sobrantes) == []
    assert set(SOLO_LEEN_EL_CASO).isdisjoint(ESCRIBEN_CON_LA_SESION_COMUN)
    assert set(QUE_ESCRIBEN).isdisjoint(hoy)


def test_toda_ruta_no_get_con_la_sesion_comun_esta_clasificada_ve_la_falta() -> None:
    """No pasa en vacio: ve un POST y un PUT con la sesion comun dentro de un `include_router`
    anidado, y no ve el GET ni la ruta con la sesion de escritura."""
    interno = APIRouter(prefix="/interno")

    @interno.post("/escribe")
    def escribe(sesion: SesionDep) -> None: ...

    @interno.put("/cambia")
    def cambia(sesion: SesionDep) -> None: ...

    @interno.get("/lee")
    def lee(sesion: SesionDep) -> None: ...

    @interno.post("/bien")
    def bien(sesion: SesionDeEscrituraDep) -> None: ...

    por_inclusion = APIRouter()

    @por_inclusion.post("/sin-firma")
    def sin_firma() -> None: ...

    externo = APIRouter(prefix="/v9")
    externo.include_router(interno, prefix="/x")
    prueba = FastAPI()
    prueba.include_router(externo, prefix="/z")
    prueba.include_router(por_inclusion, prefix="/w", dependencies=[Depends(sesion_api)])

    vistas = _no_get_con_la_sesion_comun(prueba.router)

    assert vistas == {
        ("POST", "/z/v9/x/interno/escribe"),
        ("PUT", "/z/v9/x/interno/cambia"),
        ("POST", "/w/sin-firma"),
    }
    assert {camino for _, camino in vistas} <= set(prueba.openapi()["paths"])


def test_toda_ruta_no_get_con_la_sesion_comun_esta_clasificada_ve_la_subdependencia() -> None:
    """DS-50 (1): la sesion comun que llega por una subdependencia de una dependencia del
    `include_router` (no la dependencia misma) tambien cuenta."""

    def dep(sesion: SesionDep) -> None: ...

    def de_escritura(sesion: SesionDeEscrituraDep) -> None: ...

    r = APIRouter()

    @r.post("/por-debajo")
    def por_debajo() -> None: ...

    bien = APIRouter()

    @bien.post("/bien")
    def bien_ruta() -> None: ...

    prueba = FastAPI()
    prueba.include_router(r, prefix="/s", dependencies=[Depends(dep)])
    prueba.include_router(bien, prefix="/e", dependencies=[Depends(de_escritura)])

    assert _no_get_con_la_sesion_comun(prueba.router) == {("POST", "/s/por-debajo")}
