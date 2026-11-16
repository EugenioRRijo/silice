"""Entrada hostil del escritor y de la lectura de la plantilla (depuración del lector, 2026-11-15).

Cada prueba apunta a un defecto verificado: un libro construido aquí (ningún dato real) que hacía
girar sin fin o crecer sin cota una parte del calcado. Los cuelgues se miden con un hilo y un tope
de tiempo (`_con_tope`): el hilo es demonio, así que una prueba en rojo no deja el proceso colgado.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from adapters.hoja_empresa.escritor.copia import tamano_imagen

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
