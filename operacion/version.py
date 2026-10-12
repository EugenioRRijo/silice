"""La versión de Sílice sale de un solo sitio: `pyproject.toml` (RF-99; spec S5 §9.2).

`pyproject.toml` guarda la versión en PEP 440 (`1.0.0rc1`); la etiqueta de git y el instalador usan
SemVer (`v1.0.0-rc.1`, `1.0.0-rc.1`). Las conversiones son exactas y reversibles; `packaging`
normaliza `1.0.0-rc.1` a `1.0.0rc1` y la prueba lo confirma.
"""

from __future__ import annotations

import re
import tomllib
from functools import lru_cache
from pathlib import Path

from operacion import config

_PEP = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")
_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$")
_A_SEMVER = {"a": "alpha", "b": "beta", "rc": "rc"}
_A_PEP = {nombre: letra for letra, nombre in _A_SEMVER.items()}


def ruta_pyproject() -> Path:
    return config.RAIZ / "pyproject.toml"


@lru_cache(maxsize=1)
def version() -> str:
    """La versión de `pyproject.toml`, en PEP 440."""
    with ruta_pyproject().open("rb") as archivo:
        return str(tomllib.load(archivo)["project"]["version"])


def _rechazar(texto: str) -> ValueError:
    return ValueError(f"«{texto}» no es una versión válida (X.Y.Z, con a, b o rc opcional)")


def a_semver(pep440: str) -> str:
    coincidencia = _PEP.match(pep440)
    if coincidencia is None:
        raise _rechazar(pep440)
    mayor, menor, parche, fase, numero = coincidencia.groups()
    base = f"{mayor}.{menor}.{parche}"
    return base if fase is None else f"{base}-{_A_SEMVER[fase]}.{numero}"


def a_pep440(semver: str) -> str:
    coincidencia = _SEMVER.match(semver)
    if coincidencia is None:
        raise _rechazar(semver)
    mayor, menor, parche, fase, numero = coincidencia.groups()
    base = f"{mayor}.{menor}.{parche}"
    return base if fase is None else f"{base}{_A_PEP[fase]}{numero}"


def etiqueta(pep440: str | None = None) -> str:
    return "v" + a_semver(pep440 if pep440 is not None else version())


def siguiente_parche(semver: str) -> str:
    """`1.0.0-rc.1` → `1.0.1`: mayor que la candidata y que la final (prueba de actualización)."""
    coincidencia = _SEMVER.match(semver)
    if coincidencia is None:
        raise _rechazar(semver)
    mayor, menor, parche = (int(grupo) for grupo in coincidencia.groups()[:3])
    return f"{mayor}.{menor}.{parche + 1}"
