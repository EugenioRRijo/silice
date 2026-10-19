"""RM-1: la logica de «Precios de la empresa» vive en `aplicacion/precios_empresa.py` y
`ui/precios_empresa.py` solo la reexporta. La capa de aplicacion no importa `scripts`, asi que
repite los datos de la referencia MaPreX en Bs; esta prueba los ata a los del guion que genero
el CSV."""

import ast
from pathlib import Path

import aplicacion.precios_empresa as original
import ui.precios_empresa as reexportado
from scripts.lista_maprex_bs import (
    FECHA_TASA_MAPREX,
    FUENTE_TASA_MAPREX,
    RUTA_SALIDA,
    TASA_MAPREX,
)

RAIZ = Path(__file__).resolve().parents[2]


def test_los_datos_de_la_referencia_son_los_del_guion_de_maprex() -> None:
    assert original.TASA_MAPREX == TASA_MAPREX
    assert original.FECHA_TASA_MAPREX == FECHA_TASA_MAPREX
    assert original.FUENTE_TASA_MAPREX == FUENTE_TASA_MAPREX
    assert original.RUTA_REFERENCIA_MAPREX == RUTA_SALIDA


def test_ui_precios_empresa_reexporta_la_capa_de_aplicacion() -> None:
    assert reexportado.__all__ and set(reexportado.__all__) <= set(vars(original))
    for nombre in reexportado.__all__:
        assert getattr(reexportado, nombre) is getattr(original, nombre), nombre
    arbol = ast.parse((RAIZ / "ui" / "precios_empresa.py").read_text(encoding="utf-8"))
    definiciones = [
        nodo.name
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef)
    ]
    assert definiciones == []
