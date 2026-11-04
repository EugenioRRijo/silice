"""El CSV del cómputo con la regla de Eugenio (pulido F5, tanda 2, Tarea 5).

`aplicacion.computo_csv.a_la_forma_de_siempre` deja un CSV separado por punto y coma (como lo
guarda Excel en español) en la forma que leen los adaptadores: separado por coma y con punto
decimal. En un archivo con `;`, las cifras van con coma decimal y punto de miles; uno separado por
coma no se toca. Oráculos escritos a mano; datos ficticios.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from aplicacion.cifras import MENSAJE_CIFRA
from aplicacion.computo_csv import a_la_forma_de_siempre

NUMERICAS = ("a", "h", "longitud")


def _escribir(
    carpeta: Path, texto: str, nombre: str = "computo.csv", codificacion: str = "utf-8"
) -> Path:
    ruta = carpeta / nombre
    ruta.write_bytes(texto.encode(codificacion))
    return ruta


def _filas(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


@pytest.fixture
def carpetas(tmp_path: Path) -> tuple[Path, Path]:
    origen, destino = tmp_path / "subida", tmp_path / "leida"
    origen.mkdir()
    destino.mkdir()
    return origen, destino


def test_con_punto_y_coma_la_coma_es_el_decimal_y_el_punto_los_miles(carpetas):
    origen, destino = carpetas
    ruta = _escribir(origen, "id;tipo;a;h;longitud\nT-01;tanquilla;1.234,56;0,80;12\n")

    leida = a_la_forma_de_siempre(ruta, NUMERICAS, destino)

    assert leida == destino / "computo.csv"
    assert _filas(leida) == [
        {"id": "T-01", "tipo": "tanquilla", "a": "1234.56", "h": "0.80", "longitud": "12"}
    ]


def test_con_punto_y_coma_el_punto_solo_es_de_miles(carpetas):
    origen, destino = carpetas
    ruta = _escribir(origen, "id;a;h;longitud\nZ-01;1.200;-0,5;12.345.678,9\n")

    filas = _filas(a_la_forma_de_siempre(ruta, NUMERICAS, destino))

    assert filas == [{"id": "Z-01", "a": "1200", "h": "-0.5", "longitud": "12345678.9"}]


def test_un_archivo_separado_por_coma_no_cambia(carpetas):
    origen, destino = carpetas
    texto = "id,tipo,a,h,longitud\nT-01,tanquilla,0.80,1.5,24.00\n"
    ruta = _escribir(origen, texto)

    leida = a_la_forma_de_siempre(ruta, NUMERICAS, destino)

    assert leida == ruta
    assert ruta.read_text(encoding="utf-8") == texto
    assert list(destino.iterdir()) == []


def test_las_columnas_de_texto_no_se_tocan(carpetas):
    """El código «1.234» y las especificaciones con `;` (entre comillas) quedan tal cual."""
    origen, destino = carpetas
    ruta = _escribir(
        origen,
        'id;codigo_partida;a;especificaciones\nT-01;1.234;2,5;"diametro=4,5 pulg;material=PVC"\n',
    )

    filas = _filas(a_la_forma_de_siempre(ruta, ("a",), destino))

    assert filas == [
        {
            "id": "T-01",
            "codigo_partida": "1.234",
            "a": "2.5",
            "especificaciones": "diametro=4,5 pulg;material=PVC",
        }
    ]


def test_una_celda_numerica_vacia_queda_vacia(carpetas):
    origen, destino = carpetas
    ruta = _escribir(origen, "id;a;h;longitud\nT-01;0,80;;\n")

    filas = _filas(a_la_forma_de_siempre(ruta, NUMERICAS, destino))

    assert filas == [{"id": "T-01", "a": "0.80", "h": "", "longitud": ""}]


def test_la_marca_de_utf8_de_excel_no_cambia_el_nombre_de_la_primera_columna(carpetas):
    origen, destino = carpetas
    ruta = _escribir(origen, "﻿id;a\nT-01;0,80\n")

    assert _filas(a_la_forma_de_siempre(ruta, ("a",), destino)) == [{"id": "T-01", "a": "0.80"}]


@pytest.mark.parametrize("texto", ["2.5", "1,234.5", "0.123", "1 234", "1e3", "uno"])
def test_con_punto_y_coma_una_cifra_que_no_sigue_la_regla_se_rechaza(carpetas, texto):
    """«2.5» con `;` es un punto decimal anglosajón: se rechaza con el archivo, la fila, la
    columna y la regla."""
    origen, destino = carpetas
    ruta = _escribir(origen, f"id;a\nT-01;0,80\nT-02;{texto}\n", nombre="zanjas.csv")

    with pytest.raises(ValueError) as error:
        a_la_forma_de_siempre(ruta, ("a",), destino)

    mensaje = str(error.value)
    assert "zanjas.csv" in mensaje
    assert "fila 3" in mensaje
    assert "'a'" in mensaje
    assert MENSAJE_CIFRA in mensaje


def test_una_fila_con_mas_celdas_que_la_cabecera_se_rechaza(carpetas):
    origen, destino = carpetas
    ruta = _escribir(origen, "id;a\nT-01;0,80;sobra\n", nombre="zanjas.csv")

    with pytest.raises(ValueError, match=r"zanjas\.csv.*fila 2.*más celdas que la cabecera"):
        a_la_forma_de_siempre(ruta, ("a",), destino)


def test_un_archivo_que_no_es_utf8_se_rechaza_con_su_nombre(carpetas):
    origen, destino = carpetas
    ruta = _escribir(
        origen, "id;descripción;a\nT-01;año;0,80\n", nombre="viejo.csv", codificacion="cp1252"
    )

    with pytest.raises(ValueError, match=r"viejo\.csv.*UTF-8"):
        a_la_forma_de_siempre(ruta, ("a",), destino)
