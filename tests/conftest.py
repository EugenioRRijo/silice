"""Fixtures compartidas de la suite.

Los datos viven en tests/fixtures/apu_linea_base.py (única copia, principio DRY).
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.fixtures import apu_linea_base as linea_base

#: `pytester` corre sesiones de pytest aparte: con él, `tests/unit/test_salvaguarda.py` observa la
#: salvaguarda en rojo sin tocar la base real.
pytest_plugins = ["pytester"]

#: La base de trabajo del repositorio. Ninguna prueba puede crearla, borrarla ni escribir en ella:
#: el sprint del prototipo dejó `UI-01-TUB` dentro por una prueba de interfaz mal desviada
#: (hallazgo 5 de su bitácora de cierre), y una convención escrita en docstrings no lo impidió.
RUTA_BASE_REAL = Path(__file__).resolve().parents[1] / "data" / "apu.db"


def huella(ruta: Path) -> tuple[bool, int | None, int | None]:
    """Existencia, `mtime` en nanosegundos y tamaño del archivo.

    El tamaño cubre la escritura que no mueve el `mtime` (una marca restaurada o un sistema de
    archivos de baja resolución).
    """
    if not ruta.exists():
        return (False, None, None)
    estado = ruta.stat()
    return (True, estado.st_mtime_ns, estado.st_size)


def vigilar_base(ruta: Path) -> Iterator[None]:
    """Cuerpo de la salvaguarda: falla si la huella de `ruta` cambió entre la apertura y el cierre.

    Separado de la fixture para que `tests/unit/test_salvaguarda.py` lo ejercite sobre una ruta
    temporal.
    """
    antes = huella(ruta)
    yield
    despues = huella(ruta)
    if despues != antes:
        pytest.fail(
            f"la suite modifico {ruta} (antes {antes}, despues {despues}): alguna prueba "
            "no desvio su base a tmp_path",
            pytrace=False,
        )


@pytest.fixture(scope="session", autouse=True)
def _base_real_intacta():
    """Falla la sesión entera si alguna prueba creó, borró o modificó `data/apu.db`."""
    yield from vigilar_base(RUTA_BASE_REAL)


@pytest.fixture(autouse=True)
def _sin_caso_del_entorno(monkeypatch):
    """Una `ARENIA_CASO` exportada en la terminal de quien corre la suite no debe desviar."""
    monkeypatch.delenv("ARENIA_CASO", raising=False)


@pytest.fixture(scope="session")
def parametros_linea_base():
    return linea_base.PARAMETROS_LINEA_BASE


@pytest.fixture(scope="session")
def apus_linea_base():
    return linea_base.APUS_LINEA_BASE


@pytest.fixture(scope="session")
def presupuesto_auditado():
    return linea_base.PRESUPUESTO_AUDITADO


@pytest.fixture(scope="session")
def curva_auditada():
    return linea_base.CURVA_AUDITADA
