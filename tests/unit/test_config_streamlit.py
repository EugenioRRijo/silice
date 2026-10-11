"""`.streamlit/config.toml` del repositorio (plan 0.6.0, tarea A1; maestro §4.7 y §8; S5 §1.2).

Streamlit 1.62.0 sin `server.address` escucha en todas las interfaces y envia estadisticas de uso
(S5 §1.2). Este archivo lo fija para el camino de desarrollo; S5-2 lo toma como base del archivo
oficial de `{app}\\codigo`.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from streamlit import config as config_streamlit

from adapters.espacio.planos.comun import LIMITE_BYTES

RAIZ = Path(__file__).resolve().parents[2]
CONFIG = RAIZ / ".streamlit" / "config.toml"


def _config() -> dict:
    with CONFIG.open("rb") as archivo:
        return tomllib.load(archivo)


def test_escucha_solo_en_el_bucle_local_y_sin_telemetria() -> None:
    config = _config()
    assert config["server"]["address"] == "127.0.0.1"
    assert config["browser"]["serverAddress"] == "127.0.0.1"
    assert config["browser"]["gatherUsageStats"] is False


def test_cors_y_xsrf_explicitos() -> None:
    config = _config()
    assert config["server"]["enableCORS"] is True
    assert config["server"]["enableXsrfProtection"] is True


def test_el_limite_de_subida_es_el_de_los_planos() -> None:
    """RNF-12: 20 MB, la misma cifra que `adapters/espacio/planos/comun.py:36`."""
    assert _config()["server"]["maxUploadSize"] * 1024 * 1024 == LIMITE_BYTES


def test_los_detalles_de_error_no_llegan_al_navegador() -> None:
    valor = _config()["client"]["showErrorDetails"]
    validos = {opcion.value for opcion in config_streamlit.ShowErrorDetailsConfigOptions}
    assert valor in validos
    assert valor == "none"


def test_streamlit_conoce_cada_opcion_del_archivo() -> None:
    opciones = config_streamlit.get_config_options()
    desconocidas = [
        f"{seccion}.{nombre}"
        for seccion, valores in _config().items()
        for nombre in valores
        if f"{seccion}.{nombre}" not in opciones
    ]
    assert desconocidas == []


def test_la_suite_conserva_el_detalle_de_los_errores_de_apptest() -> None:
    """AppTest lee el `config.toml` del directorio de trabajo; `tests/conftest.py` fija la variable
    `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS`, que manda sobre el archivo, para que un fallo de AppTest
    siga mostrando su mensaje real."""
    assert os.environ["STREAMLIT_CLIENT_SHOW_ERROR_DETAILS"] == "full"
