"""Adaptador del dominio sistemas: alcance funcional (Sesión I5).

Reproduce, a partir de `data/samples/sistemas/alcance_funcional.csv`, los puntos de función no
ajustados (PFNA) de cada caso de uso, con los pesos medios IFPUG declarados en
`adapters/sistemas/adaptador.py` (`REGLA_PUNTOS_FUNCION`). No repite esos pesos salvo para
recalcular el PFNA esperado directamente desde el CSV y compararlo con lo que produce el
adaptador (test de integración de la fórmula, no un número mágico copiado).
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from adapters.sistemas import AdaptadorSistemas
from adapters.sistemas.adaptador import REGLA_PUNTOS_FUNCION
from adapters.sistemas.evaluador import evaluar_regla
from core.contracts import Dominio, OrigenTipo

RAIZ = Path(__file__).resolve().parents[2]
RUTA_MUESTRA = RAIZ / "data" / "samples" / "sistemas" / "alcance_funcional.csv"

# Pesos medios de complejidad IFPUG (misma tabla documentada en el docstring del adaptador y en
# data/samples/sistemas/README.md): Entrada externa=4, Salida externa=5, Consulta externa=4,
# Archivo lógico interno=10, Archivo de interfaz externa=7.
_PESOS_IFPUG = {"entradas": 4, "salidas": 5, "consultas": 4, "archivos": 10, "interfaces": 7}


def _filas_muestra() -> list[dict[str, str]]:
    with open(RUTA_MUESTRA, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def test_extrae_los_casos_de_uso_de_la_muestra():
    adaptador = AdaptadorSistemas()
    assert adaptador.dominio is Dominio.SISTEMAS

    items = adaptador.extraer(RUTA_MUESTRA)
    filas = _filas_muestra()

    assert len(items) == len(filas)
    assert len(items) >= 8

    modulos = {fila["modulo"] for fila in filas}
    assert len(modulos) >= 3

    for item, fila in zip(items, filas, strict=True):
        assert item.origen_id == fila["id"]
        assert item.origen_id.startswith("SI-")
        assert item.codigo_partida == fila["codigo_partida"]
        assert item.unidad == "pf"
        assert item.dominio is Dominio.SISTEMAS


def test_puntos_de_funcion_no_ajustados():
    filas = _filas_muestra()
    esperados = {
        fila["id"]: Decimal(
            sum(_PESOS_IFPUG[columna] * int(fila[columna]) for columna in _PESOS_IFPUG)
        )
        for fila in filas
    }

    items = AdaptadorSistemas().extraer(RUTA_MUESTRA)
    obtenidos = {item.origen_id: item.cantidad for item in items}

    assert obtenidos == esperados
    assert all(cantidad > 0 for cantidad in obtenidos.values())


def test_items_trazables_por_regla():
    items = AdaptadorSistemas().extraer(RUTA_MUESTRA)
    assert items, "la muestra debe producir al menos un item"

    for item in items:
        assert item.origen_tipo is OrigenTipo.REGLA
        assert item.regla == REGLA_PUNTOS_FUNCION
        assert item.dominio is Dominio.SISTEMAS
        assert item.origen_id
        assert evaluar_regla(item.regla, item.parametros) == item.cantidad
        assert set(item.parametros) == set(_PESOS_IFPUG)
