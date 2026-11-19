"""El CSV de la tabla de escenarios (arbitraje de feature/vivo-control, puntos 4 y 11).

- Una cifra con más de 26 cifras enteras o no finita no tumba la ruta (`quantize` lanzaba
  `InvalidOperation` y la API daba 500): se presenta con la presentación segura de la API
  (`api.presentacion.cifra_presentada`, la misma regla que `monto`).
- El nombre de un escenario se neutraliza contra fórmulas dentro del propio CSV, también con un
  salto de línea delante o con espacios antes del «=».

Oráculos escritos a mano; escenarios ficticios.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal

import pytest

from api.presentacion import cifra_presentada
from aplicacion.escenarios_csv import csv_de_escenarios
from aplicacion.formulas import neutralizar_formula

D = Decimal


def _filas(contenido: bytes) -> list[list[str]]:
    texto = contenido.decode("utf-8")
    assert texto.startswith("\ufeff")
    return list(csv.reader(io.StringIO(texto.removeprefix("\ufeff")), delimiter=";"))


DIEZ, CERO = D("10"), D("0")


def _fila(nombre: str = "base", total=DIEZ, variacion=CERO, pct=CERO) -> dict:
    return {"escenario": nombre, "total": total, "variacion": variacion, "variacion_pct": pct}


def test_una_cifra_de_mas_de_26_cifras_enteras_sale_exacta_y_no_tumba_el_csv() -> None:
    enorme = D("123456789012345678901234567.5")  # 27 cifras enteras: quantize no cabe
    (_, fila) = _filas(csv_de_escenarios([_fila(total=enorme)], presentar=cifra_presentada))
    assert fila[1] == "123.456.789.012.345.678.901.234.567,5"


def test_una_cifra_no_finita_se_dice_no_disponible() -> None:
    (_, fila) = _filas(
        csv_de_escenarios(
            [_fila(pct=D("NaN"), variacion=D("Infinity"))], presentar=cifra_presentada
        )
    )
    assert fila[2:] == ["no disponible", "no disponible"]


def test_las_cifras_normales_van_a_dos_decimales_con_coma() -> None:
    (_, fila) = _filas(
        csv_de_escenarios(
            [
                _fila(
                    total=D("1234.565"),
                    variacion=D("-0.004"),
                    pct=D("4.545454545454545454545454545"),
                )
            ],
            presentar=cifra_presentada,
        )
    )
    assert fila[1:] == ["1.234,57", "0,00", "4,55"]


@pytest.mark.parametrize(
    "nombre",
    ['=HYPERLINK("http://x","clic")', "+1+1", "-1+1", "@SUMA(1)", "\tx", "\rx", "\n=1+1", "  =1+1"],
)
def test_el_csv_neutraliza_dentro_los_nombres_que_empiezan_como_formula(nombre: str) -> None:
    (_, fila) = _filas(csv_de_escenarios([_fila(nombre)], presentar=cifra_presentada))
    assert fila[0] == "'" + nombre


@pytest.mark.parametrize("nombre", ["cemento y arena", "utilidad 20", "Escenario = alto", ""])
def test_un_nombre_que_no_es_formula_sale_tal_cual(nombre: str) -> None:
    assert neutralizar_formula(nombre) == nombre
