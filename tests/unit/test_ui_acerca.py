"""«Acerca de»: versión, las dos revisiones, carpeta de datos y módulos (RF-99; spec S5 §5.2).

Oráculos independientes: la versión se lee del texto de `pyproject.toml` y la revisión de cada
base, de su tabla `alembic_version` con `sqlite3` (no con `operacion.base_datos`).
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path

from streamlit.testing.v1 import AppTest

from operacion import config
from operacion.base_datos import Destino, preparar_base


def _version_de_pyproject() -> str:
    texto = (config.RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    proyecto = texto.split("[project]", 1)[1]
    return re.search(r'(?m)^version\s*=\s*"([^"]+)"', proyecto).group(1)


def _revision_en_disco(ruta: Path) -> str:
    with closing(sqlite3.connect(ruta)) as conexion:
        (revision,) = conexion.execute("SELECT version_num FROM alembic_version").fetchone()
    return revision


def _bases() -> tuple[str, str]:
    preparar_base(config.ruta_instalacion(), Destino.INSTALACION)
    preparar_base(config.ruta_caso_por_defecto())
    return (
        _revision_en_disco(config.ruta_instalacion()),
        _revision_en_disco(config.ruta_caso_por_defecto()),
    )


def _pagina() -> None:
    from ui.paginas import acerca as pagina

    pagina.render()


def test_la_pantalla_muestra_todo_sin_excepciones() -> None:
    instalacion, caso = _bases()
    at = AppTest.from_function(_pagina).run()
    assert not at.exception
    texto = " ".join(m.value for m in at.markdown)
    assert _version_de_pyproject() in texto
    assert instalacion in texto and caso in texto
    assert str(config.carpeta_datos()) in texto and "Similitud de partidas" in texto
    assert "LICENCIAS" in " ".join(c.value for c in at.caption)


def test_la_pantalla_no_crea_bases() -> None:
    at = AppTest.from_function(_pagina).run()
    assert not at.exception and "sin base" in " ".join(m.value for m in at.markdown)
    assert not config.ruta_instalacion().exists()
