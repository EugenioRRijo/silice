"""Guardia del archivo subido antes de abrirlo (Silice 1.5, RF-102, RNF-21; F-D10 y errata 8).

Cada límite se prueba en su frontera: el valor máximo pasa y el máximo + 1 se rechaza. Los
contenedores se arman en la prueba con `zipfile` (piezas sin comprimir cuando hace falta controlar
la razón de compresión). Oráculo: las constantes publicadas del módulo y el área de cada rango
calculada a mano (filas × columnas).
"""

from __future__ import annotations

import io
import random
import zipfile

import pytest

from adapters.hoja_empresa.guardia import (
    MAX_AREA_HOJA,
    MAX_BYTES,
    MAX_COMBINADAS,
    MAX_DESCOMPRIMIDO,
    MAX_ENTRADAS,
    MAX_PIEZA,
    MAX_RAZON,
    ArchivoRechazado,
    _verificar_contenedor,
    verificar_archivo,
)
from tests.fixtures.libros_empresa import libro_limpio

NOMBRE = "libro.xlsx"


def _zip(piezas: dict[str, bytes], metodo: int = zipfile.ZIP_STORED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", metodo) as z:
        for nombre, contenido in piezas.items():
            z.writestr(nombre, contenido)
    return buf.getvalue()


def _con_hoja(xml: str) -> bytes:
    return _zip({"xl/workbook.xml": b"<workbook/>", "xl/worksheets/sheet1.xml": xml.encode()})


def _info(nombre: str, tamano: int, comprimido: int) -> zipfile.ZipInfo:
    z = zipfile.ZipInfo(nombre)
    z.file_size = tamano
    z.compress_size = comprimido
    return z


def test_las_constantes_son_las_del_spec():
    """F-D10 y la revisión de seguridad 1.5: 25 MiB, 5 000 entradas, 60/30 MiB, razón 200,
    200 000 combinadas, 2 000 000 de celdas declaradas por hoja."""
    assert MAX_BYTES == 25 * 2**20
    assert MAX_ENTRADAS == 5000
    assert (MAX_DESCOMPRIMIDO, MAX_PIEZA) == (60 * 2**20, 30 * 2**20)
    assert MAX_RAZON == 200
    assert (MAX_COMBINADAS, MAX_AREA_HOJA) == (200_000, 2_000_000)


def test_libro_limpio_pasa():
    verificar_archivo(libro_limpio().datos, NOMBRE)


@pytest.mark.parametrize(
    ("nombre", "texto"),
    [
        ("libro.xlsm", "macros (.xlsm)"),
        ("libro.xlsb", "binario (.xlsb)"),
        ("libro.xls", "Excel 97-2003"),
        ("libro.xltm", "plantilla con macros"),
        ("libro.csv", "extensión '.csv'"),
        ("libro", "no tiene extensión"),
        ("carpeta/libro.xlsx.exe", "extensión '.exe'"),
    ],
)
def test_extension_distinta_de_xlsx_se_rechaza(nombre, texto):
    with pytest.raises(ArchivoRechazado, match=texto.replace("(", r"\(").replace(")", r"\)")):
        verificar_archivo(libro_limpio().datos, nombre)


def test_extension_en_mayusculas_y_ruta_de_windows_se_aceptan():
    verificar_archivo(libro_limpio().datos, "C:\\obras\\LIBRO.XLSX")


def test_tamano_maximo_pasa_y_uno_mas_se_rechaza():
    # Con MAX_BYTES exactos el tamaño no es el motivo (los bytes no son un ZIP: otro mensaje).
    with pytest.raises(ArchivoRechazado, match="no es un libro .xlsx válido"):
        verificar_archivo(b"\0" * MAX_BYTES, NOMBRE)
    with pytest.raises(ArchivoRechazado, match="supera el máximo de 25 MiB"):
        verificar_archivo(b"\0" * (MAX_BYTES + 1), NOMBRE)


def test_bytes_que_no_son_zip_se_rechazan():
    with pytest.raises(ArchivoRechazado, match="no es un libro .xlsx válido"):
        verificar_archivo(b"PK esto no es un zip", NOMBRE)


def test_macros_dentro_de_un_xlsx_se_rechazan():
    datos = _zip({"xl/workbook.xml": b"<workbook/>", "xl/vbaProject.bin": b"\0" * 10})
    with pytest.raises(ArchivoRechazado, match="vbaProject.bin"):
        verificar_archivo(datos, NOMBRE)


def test_zip_sin_workbook_se_rechaza():
    with pytest.raises(ArchivoRechazado, match="falta xl/workbook.xml"):
        verificar_archivo(_zip({"otra.xml": b"<x/>"}), NOMBRE)


def test_numero_de_entradas_en_su_frontera():
    base = [_info("xl/workbook.xml", 10, 10)]
    _verificar_contenedor(base + [_info(f"p{i}", 1, 1) for i in range(MAX_ENTRADAS - 1)], NOMBRE)
    with pytest.raises(ArchivoRechazado, match="5001 piezas"):
        _verificar_contenedor(base + [_info(f"p{i}", 1, 1) for i in range(MAX_ENTRADAS)], NOMBRE)


def test_razon_de_compresion_por_pieza_en_su_frontera():
    wb = _info("xl/workbook.xml", 10, 10)
    _verificar_contenedor([wb, _info("a.xml", 200 * 1000, 1000)], NOMBRE)
    with pytest.raises(ArchivoRechazado, match=r"a\.xml\) con una compresión anómala"):
        _verificar_contenedor([wb, _info("a.xml", 200 * 1000 + 1, 1000)], NOMBRE)
    with pytest.raises(ArchivoRechazado, match="compresión anómala"):
        _verificar_contenedor([wb, _info("a.xml", 10, 0)], NOMBRE)


def test_tamano_descomprimido_por_pieza_y_total_en_su_frontera():
    wb = _info("xl/workbook.xml", 10, 10)
    _verificar_contenedor([wb, _info("a.xml", MAX_PIEZA, MAX_PIEZA)], NOMBRE)
    with pytest.raises(ArchivoRechazado, match="supera el máximo de 30 MiB por pieza"):
        _verificar_contenedor([wb, _info("a.xml", MAX_PIEZA + 1, MAX_PIEZA)], NOMBRE)
    mitad = MAX_DESCOMPRIMIDO // 2
    _verificar_contenedor(
        [_info("xl/workbook.xml", 0, 0), _info("a", mitad, mitad), _info("b", mitad, mitad)],
        NOMBRE,
    )
    with pytest.raises(ArchivoRechazado, match="supera el máximo de 60 MiB"):
        _verificar_contenedor(
            [
                _info("xl/workbook.xml", 1, 1),
                _info("a", mitad, mitad),
                _info("b", mitad, mitad),
            ],
            NOMBRE,
        )


def test_celdas_combinadas_en_su_frontera():
    # A1:A200000 cubre 200 000 celdas (1 columna × 200 000 filas): el máximo pasa.
    verificar_archivo(_con_hoja('<mergeCells><mergeCell ref="A1:A200000"/></mergeCells>'), NOMBRE)
    # Dos combinaciones que suman 200 001 se rechazan (se suman en todo el libro).
    xml = '<mergeCell ref="A1:A200000"/><mergeCell ref="C1:C1"/>'
    with pytest.raises(ArchivoRechazado, match="combina más de 200.000 celdas"):
        verificar_archivo(_con_hoja(xml), NOMBRE)


def test_rango_con_esquinas_invertidas_y_signos_dolar():
    # $B$2:$A$1 = 2 × 2 = 4 celdas; 50 000 de ellos = 200 000 (pasa), uno más rechaza.
    una = '<mergeCell ref="$B$2:$A$1"/>'
    verificar_archivo(_con_hoja(una * 50_000), NOMBRE)
    with pytest.raises(ArchivoRechazado, match="combina más de"):
        verificar_archivo(_con_hoja(una * 50_000 + '<mergeCell ref="A1"/>'), NOMBRE)


def test_dimension_declarada_por_hoja_en_su_frontera():
    # A1:CV20000 = 100 columnas × 20 000 filas = 2 000 000: pasa; una fila más se rechaza.
    verificar_archivo(_con_hoja('<dimension ref="A1:CV20000"/>'), NOMBRE)
    with pytest.raises(ArchivoRechazado, match=r"declara 2\.000\.100 celdas"):
        verificar_archivo(_con_hoja('<dimension ref="A1:CV20001"/>'), NOMBRE)


def test_dimension_xfd_completa_se_rechaza():
    with pytest.raises(ArchivoRechazado, match="declara"):
        verificar_archivo(_con_hoja('<x:dimension ref="A1:XFD1048576"/>'), NOMBRE)


def test_etiqueta_partida_entre_dos_bloques_se_cuenta_una_vez():
    """El barrido lee de a 1 MiB con solape: una combinación de 150 000 celdas que cruza el corte
    no se cuenta dos veces (300 000 rechazaría por error)."""
    relleno = random.Random(0).randbytes(2**20 - 10).replace(b"<", b"x")
    etiqueta = b'<mergeCell ref="A1:A150000"/>'
    pieza = relleno + etiqueta + b"x" * 100
    datos = _zip({"xl/workbook.xml": b"<workbook/>", "xl/worksheets/sheet1.xml": pieza})
    verificar_archivo(datos, NOMBRE)


def test_referencia_que_no_es_de_celdas_no_cuenta():
    verificar_archivo(_con_hoja('<mergeCell ref="Hoja!nombre"/><dimension ref="A:A"/>'), NOMBRE)
