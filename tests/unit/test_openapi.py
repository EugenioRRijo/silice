import json
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "docs" / "api.json"


def test_el_esquema_exportado_cubre_las_rutas_clave():
    esquema = json.loads(RUTA.read_text(encoding="utf-8"))
    rutas = esquema["paths"]
    for esperada in (
        "/salud",
        "/partidas",
        "/listas-precios",
        "/computos/{dominio}",
        "/presupuestos",
        "/presupuestos/{codigo}/actualizacion",
    ):
        assert esperada in rutas, esperada


def test_el_esquema_esta_al_dia_con_la_aplicacion():
    from api.main import app

    assert (
        json.loads(RUTA.read_text(encoding="utf-8"))["paths"].keys()
        == app.openapi()["paths"].keys()
    )


def test_los_modelos_de_aprobaciones_no_chocan_con_los_de_otros_routers():
    """Dos modelos con el mismo nombre en routers distintos hacen que FastAPI renombre los dos
    componentes con su módulo (`api__rutas__obras__ObraRespuesta`...), y el contrato de rutas
    ajenas cambia en `docs/api.json`. Cada modelo de `/v1/aprobaciones` sale con su propio nombre
    (ninguno renombrado) y ningún componente lleva el módulo de aprobaciones (T18)."""
    from pydantic import BaseModel

    from api.main import app
    from api.rutas import aprobaciones

    componentes = app.openapi()["components"]["schemas"]
    modelos = {
        nombre
        for nombre, valor in vars(aprobaciones).items()
        if isinstance(valor, type)
        and issubclass(valor, BaseModel)
        and valor.__module__ == aprobaciones.__name__
    }
    assert len(modelos) == 18  # 17 de T18 y la cadena de versiones del detalle
    assert sorted(modelos - componentes.keys()) == []
    assert [n for n in componentes if n.startswith("api__rutas__aprobaciones__")] == []
