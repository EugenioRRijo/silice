import importlib


def test_las_paginas_se_importan_sin_efectos():
    for mod in (
        "ui.app",
        "ui.paginas.actualizacion",
        "ui.paginas.catalogo",
        "ui.paginas.componer",
        "ui.paginas.elaborar",
        "ui.paginas.escenarios",
        "ui.paginas.historico",
        "ui.paginas.similares",
        "ui.paginas.simulador",
        "ui.paginas.visor",
    ):
        importlib.import_module(mod)
