"""Fixtures compartidas de la suite.

Los datos viven en tests/fixtures/apu_linea_base.py (única copia, principio DRY).

Tres guardias de sesión: la base real intacta, las variables de Sílice del entorno fuera y la
guardia de red única (maestro §6.3, RV-17): ninguna prueba se conecta fuera de 127.0.0.1 y ::1.
"""

import os
import socket
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import pytest

from tests.fixtures import apu_linea_base as linea_base
from ui.entorno import ALIAS_ANTERIORES

#: AppTest lee el `.streamlit/config.toml` del directorio de trabajo, que oculta los detalles de los
#: errores (`client.showErrorDetails = "none"`, S5 §10.1). Las variables `STREAMLIT_*` mandan sobre
#: el archivo: la suite conserva el mensaje completo de cada excepcion de AppTest.
os.environ["STREAMLIT_CLIENT_SHOW_ERROR_DETAILS"] = "full"

#: La suite corre sin red: Hugging Face lee esta variable al importarse y la guardia de red
#: bloquearia cualquier descarga. El modelo se baja antes, una vez, con
#: `scripts/descargar_modelo.py`.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

#: Destinos a los que una prueba puede conectarse (maestro §6.3, RV-17): el bucle local.
DESTINOS_PERMITIDOS = frozenset({"127.0.0.1", "::1", "localhost"})

#: Cada conexion bloqueada en la sesion, como `repr` de su direccion. Si una prueba se traga el
#: error, la sesion falla igual al cerrar (`veredicto_de_la_guardia`).
INTENTOS_BLOQUEADOS: list[str] = []


class ConexionSalienteBloqueada(OSError):  # noqa: N818 (nombre fijado por el plan 0.6.0, A3)
    """Una prueba intento conectarse fuera del equipo. Es `OSError`, como la red ausente real."""


def destino_permitido(familia: int, direccion: object) -> bool:
    """True si el destino es el bucle local; las familias que no son IP no salen del equipo."""
    if familia not in (socket.AF_INET, socket.AF_INET6):
        return True
    anfitrion = direccion[0] if isinstance(direccion, tuple) and direccion else direccion
    return str(anfitrion).split("%", 1)[0] in DESTINOS_PERMITIDOS


def veredicto_de_la_guardia(intentos: Sequence[str]) -> str | None:
    """El mensaje de fallo de la sesion si hubo intentos bloqueados; `None` si no hubo ninguno."""
    if not intentos:
        return None
    return (
        f"guardia de red: la suite intento {len(intentos)} conexion(es) fuera del equipo: "
        + ", ".join(intentos[:5])
    )


def _vigilar(original: Callable) -> Callable:
    def conectar(sock: socket.socket, direccion: object):
        if not destino_permitido(sock.family, direccion):
            INTENTOS_BLOQUEADOS.append(repr(direccion))
            raise ConexionSalienteBloqueada(
                f"guardia de red (tests/conftest.py): conexion bloqueada hacia {direccion!r}; "
                "la suite solo admite 127.0.0.1 y ::1 (RV-17)"
            )
        return original(sock, direccion)

    return conectar


#: `pytester` corre sesiones de pytest aparte: con él, `tests/unit/test_salvaguarda.py` observa la
#: salvaguarda en rojo sin tocar la base real.
pytest_plugins = ["pytester"]

#: La base de trabajo del repositorio. Ninguna prueba puede crearla, borrarla ni escribir en ella:
#: el sprint del prototipo dejó `UI-01-TUB` dentro por una prueba de interfaz mal desviada
#: (hallazgo 5 de su bitácora de cierre), y una convención escrita en docstrings no lo impidió.
RUTA_BASE_REAL = Path(__file__).resolve().parents[1] / "data" / "apu.db"

#: La base de la instalacion de desarrollo (S5-1, maestro §4.2): ninguna prueba la crea ni la toca.
RUTA_INSTALACION_REAL = RUTA_BASE_REAL.parent / "instalacion.db"


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
def _sin_variables_de_silice_del_entorno(monkeypatch):
    """Una `SILICE_*` (o su alias `ARENIA_*`) exportada en la terminal no debe desviar la suite."""
    for nombre in (*ALIAS_ANTERIORES, *ALIAS_ANTERIORES.values()):
        monkeypatch.delenv(nombre, raising=False)


@pytest.fixture(scope="session", autouse=True)
def _instalacion_real_intacta():
    """Falla la sesión si alguna prueba creó o modificó `data/instalacion.db`."""
    yield from vigilar_base(RUTA_INSTALACION_REAL)


@pytest.fixture(autouse=True)
def _datos_de_silice_temporales(monkeypatch, tmp_path_factory):
    """Toda prueba trabaja con una carpeta de datos temporal (`SILICE_DATOS`): nada llega a
    `data/casos/`, `data/respaldos/` ni `data/instalacion.db` (spec S5 §12)."""
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path_factory.mktemp("silice_datos")))
    monkeypatch.delenv("SILICE_INSTALACION", raising=False)
    monkeypatch.delenv("SILICE_RESPALDOS", raising=False)


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


@pytest.fixture(scope="session", autouse=True)
def _guardia_de_red() -> Iterator[None]:
    """Guardia de red unica (RV-17): toda la sesion solo conecta con el bucle local."""
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(socket.socket, "connect", _vigilar(socket.socket.connect))
        parche.setattr(socket.socket, "connect_ex", _vigilar(socket.socket.connect_ex))
        yield
    mensaje = veredicto_de_la_guardia(INTENTOS_BLOQUEADOS)
    if mensaje is not None:
        pytest.fail(mensaje, pytrace=False)
