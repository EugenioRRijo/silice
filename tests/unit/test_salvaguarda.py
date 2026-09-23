"""La salvaguarda de `data/apu.db` (`tests/conftest.py`) observada en verde y en rojo.

Cada caso corre una sesión de pytest aparte (`pytester`) con la misma lógica de la fixture
(`vigilar_base`), pero apuntando a un archivo de `tmp_path`: la base real no se toca ni siquiera
para demostrar que la salvaguarda muerde (INV‑065; hallazgo Q1 de la revisión del plan de C1).

Los tres casos: una base intacta deja pasar la sesión; una base que una prueba crea la hace
fallar; una base existente que una prueba modifica la hace fallar aunque conserve el `mtime`,
porque el tamaño también entra en la huella.
"""

from __future__ import annotations

CONFTEST_INTERNO = '''
from pathlib import Path

import pytest

from tests.conftest import vigilar_base

RUTA = Path({ruta!r})


@pytest.fixture(scope="session", autouse=True)
def _base_intacta():
    yield from vigilar_base(RUTA)
'''


def _correr(pytester, ruta, cuerpo):
    """Una sesión con la salvaguarda sobre `ruta` y una sola prueba que ejecuta `cuerpo`."""
    pytester.makeconftest(CONFTEST_INTERNO.format(ruta=str(ruta)))
    pytester.makepyfile(
        test_interna=(
            "import os\n"
            "from pathlib import Path\n\n"
            f"RUTA = Path({str(ruta)!r})\n\n\n"
            "def test_interna():\n"
            f"    {cuerpo}\n"
        )
    )
    return pytester.runpytest("-p", "no:cacheprovider")


def test_una_base_intacta_deja_pasar_la_sesion(pytester, tmp_path):
    ruta = tmp_path / "apu.db"
    ruta.write_bytes(b"base")

    resultado = _correr(pytester, ruta, "assert RUTA.read_bytes() == b'base'")

    resultado.assert_outcomes(passed=1)


def test_una_base_creada_por_una_prueba_hace_fallar_la_sesion(pytester, tmp_path):
    ruta = tmp_path / "apu.db"

    resultado = _correr(pytester, ruta, "RUTA.touch()")

    resultado.assert_outcomes(passed=1, errors=1)
    resultado.stdout.fnmatch_lines(["*la suite modifico*antes (False, None, None)*"])


def test_una_base_modificada_hace_fallar_la_sesion_aunque_conserve_el_mtime(pytester, tmp_path):
    """El tamaño entra en la huella: una escritura que restaura el `mtime`, o que cae en la misma
    marca de tiempo de un sistema de archivos de baja resolución, sigue detectándose."""
    ruta = tmp_path / "apu.db"
    ruta.write_bytes(b"base")
    marca = ruta.stat().st_mtime_ns

    resultado = _correr(
        pytester,
        ruta,
        f"RUTA.write_bytes(b'base modificada'); os.utime(RUTA, ns=({marca}, {marca}))",
    )

    resultado.assert_outcomes(passed=1, errors=1)
    resultado.stdout.fnmatch_lines(["*la suite modifico*"])
