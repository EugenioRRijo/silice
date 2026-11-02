"""Acerca de (`aplicacion/acerca.py`): version, revisiones de las dos bases y modulos (RF-99).

Movidas desde `tests/unit/test_ui_acerca.py` (retiro de Streamlit, F3). La pantalla solo envolvia
`aplicacion.acerca.datos_acerca` con la ruta del caso de la sesion; aqui se pasa la del caso por
defecto (`config.ruta_caso_por_defecto()`), que es la que `ui.caso.ruta_caso` devolvia en estas
pruebas. Cada prueba conserva su caso y sus aserciones. Oraculos independientes: la version del
texto de `pyproject.toml` y la revision de cada base con `sqlite3`.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path

from aplicacion import acerca
from operacion import config
from operacion.base_datos import Destino, preparar_base


def _datos_acerca(**kwargs):
    return acerca.datos_acerca(config.ruta_caso_por_defecto(), **kwargs)


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


def test_los_datos_traen_la_version_y_las_revisiones_de_las_dos_bases() -> None:
    instalacion, caso = _bases()
    datos = _datos_acerca()
    assert datos.version == _version_de_pyproject()
    fases = {"a": "alpha", "b": "beta", "rc": "rc"}  # 1.0.0rc1 → 1.0.0-rc.1 (spec S5 §9.2)
    assert datos.semver == re.sub(
        r"(a|b|rc)(\d+)$", lambda m: f"-{fases[m[1]]}.{m[2]}", datos.version
    )
    assert (datos.revision_instalacion, datos.revision_caso) == (instalacion, caso)
    # recién preparadas, cada una está en la última revisión que conoce esta versión
    assert datos.head_instalacion == instalacion and datos.head_caso == caso
    assert datos.carpeta_datos == str(config.carpeta_datos())


def test_una_base_que_no_existe_se_dice_sin_crearla() -> None:
    datos = _datos_acerca()
    assert datos.revision_instalacion == "sin base" and datos.revision_caso == "sin base"
    assert not config.ruta_instalacion().exists()
    assert not config.ruta_caso_por_defecto().exists()


def test_una_base_sin_alembic_version_lo_dice() -> None:
    ruta = config.ruta_instalacion()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("CREATE TABLE otra (id INTEGER)")
        conexion.commit()
    assert _datos_acerca().revision_instalacion == "sin alembic_version"


def test_una_base_ilegible_lo_dice_sin_excepcion() -> None:
    ruta = config.ruta_instalacion()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(b"esto no es sqlite" * 100)
    assert _datos_acerca().revision_instalacion == "ilegible"


def test_los_modulos_dicen_si_estan_instalados() -> None:
    datos = _datos_acerca(modulo_instalado=lambda nombre: nombre == "xlrd")
    modulos = dict(datos.modulos)
    assert modulos == {
        "Similitud de partidas": False,
        "Anomalías de precios": False,
        "Planos IFC": False,
        "Planos DXF": False,
        "Informes PDF": False,
        "Datos del BCV": True,
        "Asistente de IA": False,
    }


def test_un_modulo_que_no_existe_se_da_por_no_instalado() -> None:
    assert acerca._instalado("paquete_que_no_existe_en_silice") is False
    assert acerca._instalado("json") is True
