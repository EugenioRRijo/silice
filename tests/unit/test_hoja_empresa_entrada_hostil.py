"""Entrada hostil del escritor y de la lectura de la plantilla (depuración del lector, 2026-11-15).

Cada prueba apunta a un defecto verificado: un libro construido aquí (ningún dato real) que hacía
girar sin fin o crecer sin cota una parte del calcado. Los cuelgues se miden con un hilo y un tope
de tiempo (`_con_tope`): el hilo es demonio, así que una prueba en rojo no deja el proceso colgado.
"""

from __future__ import annotations

import io
import threading
from collections.abc import Callable, Iterator, Mapping
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import openpyxl

from adapters.hoja_empresa.escritor import escribir_devolucion
from adapters.hoja_empresa.escritor.copia import tamano_imagen
from adapters.hoja_empresa.guardia import MAX_FILAS_HOJA
from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import Celda, DatosDevolucion, Rotulo
from adapters.hoja_empresa.plantilla import filas_base_mo
from adapters.hoja_empresa.reglas import reglas_del_libro
from tests.fixtures.libros_empresa import libro_limpio

#: Segundos que se le dan a cada llamada; la entrada sana tarda milésimas.
TOPE = 5.0


def _con_tope(fn: Callable[..., Any], *args: Any, segundos: float = TOPE) -> Any:
    """Corre `fn(*args)` en un hilo; falla si no termina en `segundos` y relanza su excepción."""
    res: dict[str, Any] = {}

    def correr() -> None:
        try:
            res["valor"] = fn(*args)
        except BaseException as exc:  # noqa: BLE001 (se relanza en el hilo de la prueba)
            res["error"] = exc

    hilo = threading.Thread(target=correr, daemon=True)
    hilo.start()
    hilo.join(segundos)
    assert not hilo.is_alive(), f"{fn.__name__} no terminó en {segundos:g} s"
    if "error" in res:
        raise res["error"]
    return res["valor"]


# --- 1. Dimensiones de un JPEG que se acaba tras una marca ---------------------------------------


def _jpeg_con_relleno() -> bytes:
    """JPEG que Pillow abre: un byte de relleno 0xFF antes del SOF y una marca `FF E0` al final.

    El lector de cabeceras toma `FF FF` por marca y `FF C0` por su largo (65 472): salta casi al
    final y encuentra `FF E0` sin largo detrás.
    """
    cuerpo = (
        b"\xff\xd8\xff"
        + b"\xff\xc0"
        + bytes.fromhex("000b080010001001011100")
        + b"\xff\xda"
        + bytes.fromhex("0008010100003f00")
    )
    total = 6 + 0xC000
    return cuerpo + b"\x00" * (total - 2 - len(cuerpo)) + b"\xff\xe0"


def test_jpeg_que_se_acaba_tras_una_marca_no_cuelga():
    for datos in (b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe0\x00", _jpeg_con_relleno()):
        assert _con_tope(tamano_imagen, datos) is None


def test_jpeg_con_largo_menor_que_dos_no_cuelga():
    """Un segmento con largo 0 o 1 no avanza el flujo (el largo cuenta sus propios 2 bytes)."""
    for largo in (b"\x00\x00", b"\x00\x01"):
        assert _con_tope(tamano_imagen, b"\xff\xd8\xff\xe0" + largo + b"\x00" * 8) is None


def test_jpeg_sano_sigue_dando_su_tamano():
    app0 = b"\xff\xe0\x00\x10" + b"JFIF\x00" + b"\x00" * 9
    sof = b"\xff\xc0\x00\x11\x08" + (48).to_bytes(2, "big") + (64).to_bytes(2, "big") + b"\x03"
    assert _con_tope(tamano_imagen, b"\xff\xd8" + app0 + sof + b"\x00" * 9) == (64, 48)


# --- 2. Rangos de fórmula sin cota (`=SUM(G1:G10000000)`) ---------------------------------------


def _base_mo(formula: str) -> frozenset[int] | None:
    apu = SimpleNamespace(rotulos={Rotulo.BASE_MO: Celda("APU-01", "G50")})
    return filas_base_mo(apu, SimpleNamespace(formulas={"APU-01!G50": formula}))


def test_filas_base_mo_no_expande_un_rango_mas_alla_del_tope_de_filas():
    """El lector no deja pasar una hoja con algo escrito más allá de `MAX_FILAS_HOJA`: las filas
    de más del rango están vacías y expandirlas costaba segundos y gigas (10⁷ filas: 29 s, 1 GiB).
    """
    filas = _base_mo("=SUM(G1:G1000000)")
    assert filas is not None
    assert max(filas) == MAX_FILAS_HOJA
    assert len(filas) == MAX_FILAS_HOJA


def test_filas_base_mo_de_los_rangos_normales_no_cambia():
    assert _base_mo("=SUM(G19:G21)") == frozenset({19, 20, 21})
    assert _base_mo("=SUM($G$17:$G$18)+G23") == frozenset({17, 18, 23})
    assert _base_mo("=G19+G20") == frozenset({19, 20})
    assert _base_mo(f"=SUM(G{MAX_FILAS_HOJA - 1}:G{MAX_FILAS_HOJA + 5})") == frozenset(
        {MAX_FILAS_HOJA - 1, MAX_FILAS_HOJA}
    )


class _Vigilado(Mapping[str, str]):
    """Las fórmulas del libro, anotando cada fila pedida de una hoja más allá del tope."""

    def __init__(self, base: Mapping[str, str], hoja: str) -> None:
        self._base = dict(base)
        self._hoja = hoja
        self.lejanas = 0

    def __getitem__(self, clave: str) -> str:
        hoja, _, ref = clave.partition("!")
        if hoja == self._hoja and int("".join(c for c in ref if c.isdigit())) > MAX_FILAS_HOJA:
            self.lejanas += 1
        return self._base[clave]

    def __iter__(self) -> Iterator[str]:
        return iter(self._base)

    def __len__(self) -> int:
        return len(self._base)


def test_regla_l9_del_resumen_no_recorre_filas_mas_alla_del_tope():
    libro = leer_libro(libro_limpio().datos, "sintetico.xlsx")
    formulas = dict(libro.formulas)
    formulas["RESUMEN!B10"] = "=SUM(B4:B1000000)"
    vigilado = _Vigilado(formulas, "RESUMEN")
    reglas_del_libro(replace(libro, formulas=vigilado))
    assert vigilado.lejanas == 0


# --- 3. Nombre de la hoja nueva cuando el libro ya trae una con ese nombre -----------------------


def test_hoja_nueva_con_nombres_ocupados_no_cuelga_y_toma_un_numero_libre():
    """Devolver un libro ya devuelto varias veces: el sufijo « (S)» recortado a 31 caracteres
    llegaba a un punto fijo ('ALERTAS USD-Bs (S) (S) (S) ( (S') y el bucle no terminaba."""
    ocupados = (
        "ALERTAS USD-Bs",
        "ALERTAS USD-Bs (S)",
        "ALERTAS USD-Bs (S) (S)",
        "ALERTAS USD-Bs (S) (S) (S)",
        "ALERTAS USD-Bs (S) (S) (S) (S)",
        "ALERTAS USD-Bs (S) (S) (S) ( (S",
        "AUDITORÍA",
        "AUDITORÍA (2)",
    )
    wb = openpyxl.load_workbook(io.BytesIO(libro_limpio().datos))
    for nombre in ocupados:
        wb.create_sheet(nombre)["A1"] = "copia anterior"
    flujo = io.BytesIO()
    wb.save(flujo)
    datos = flujo.getvalue()
    libro = leer_libro(datos, "devuelto.xlsx")
    salida = _con_tope(
        escribir_devolucion,
        datos,
        DatosDevolucion(libro=libro, apus={}, precios_unitarios={}, totales={}),
        segundos=60.0,
    )
    hojas = openpyxl.load_workbook(io.BytesIO(salida)).sheetnames
    assert hojas[-3:] == ["AUDITORÍA (3)", "TRAZABILIDAD", "ALERTAS USD-Bs (2)"]
    assert set(ocupados) <= set(hojas)


def test_hoja_nueva_no_choca_con_una_del_libro_que_solo_cambia_en_mayusculas():
    """Excel no distingue mayúsculas en el nombre de una hoja: «Alertas USD-Bs» ya ocupa el de
    «ALERTAS USD-Bs» y xlsxwriter lanzaba `DuplicateWorksheetName` y tumbaba la devolución. El
    sufijo libre también se busca sin distinguir mayúsculas («trazabilidad (2)» ocupa el 2)."""
    ocupados = ("Alertas USD-Bs", "Trazabilidad", "trazabilidad (2)")
    wb = openpyxl.load_workbook(io.BytesIO(libro_limpio().datos))
    for nombre in ocupados:
        wb.create_sheet(nombre)["A1"] = "copia anterior"
    flujo = io.BytesIO()
    wb.save(flujo)
    datos = flujo.getvalue()
    libro = leer_libro(datos, "devuelto.xlsx")
    salida = _con_tope(
        escribir_devolucion,
        datos,
        DatosDevolucion(libro=libro, apus={}, precios_unitarios={}, totales={}),
        segundos=60.0,
    )
    hojas = openpyxl.load_workbook(io.BytesIO(salida)).sheetnames
    assert hojas[-3:] == ["AUDITORÍA", "TRAZABILIDAD (3)", "ALERTAS USD-Bs (2)"]
    assert set(ocupados) <= set(hojas)
