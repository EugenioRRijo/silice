"""Una sola fuente de la versión (RF-99; spec S5 §9.2).

Oráculo independiente: la versión esperada se saca del texto de `pyproject.toml` con una expresión
regular (no con `operacion.version`), y las conversiones PEP 440 ↔ SemVer se contrastan con
literales escritos a mano y con `packaging.version`, que es la biblioteca de la CI.
"""

from __future__ import annotations

import json
import re
import tomllib

import pytest
from packaging.version import Version

from api.main import app
from operacion import config
from operacion import version as v


def _version_en_el_texto() -> str:
    """`version = "…"` de la tabla `[project]`, leída como texto (sin `tomllib`)."""
    texto = (config.RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    proyecto = texto.split("[project]", 1)[1].split("\n[", 1)[0]
    (hallada,) = re.findall(r'(?m)^version\s*=\s*"([^"]+)"', proyecto)
    return hallada


def test_la_version_sale_de_pyproject() -> None:
    assert v.ruta_pyproject() == config.RAIZ / "pyproject.toml"
    with v.ruta_pyproject().open("rb") as archivo:
        esperada = tomllib.load(archivo)["project"]["version"]
    assert v.version() == esperada == _version_en_el_texto()


def test_la_version_de_la_api_es_la_de_pyproject() -> None:
    assert app.version == _version_en_el_texto()


def test_el_esquema_exportado_lleva_la_misma_version() -> None:
    """`docs/api.json` se regenera con la versión de `pyproject.toml` (bitácora T4)."""
    esquema = json.loads((config.RAIZ / "docs" / "api.json").read_text(encoding="utf-8"))
    assert esquema["info"]["version"] == _version_en_el_texto()


@pytest.mark.parametrize(
    ("pep", "semver"),
    [
        ("1.0.0", "1.0.0"),
        ("1.0.0rc1", "1.0.0-rc.1"),
        ("1.0.0rc12", "1.0.0-rc.12"),
        ("0.9.0a2", "0.9.0-alpha.2"),
        ("0.9.0b3", "0.9.0-beta.3"),
        ("10.20.30", "10.20.30"),
    ],
)
def test_conversion_de_ida_y_vuelta_y_packaging_la_normaliza(pep: str, semver: str) -> None:
    assert v.a_semver(pep) == semver
    assert v.a_pep440(semver) == pep
    # S5 §9.2: que 1.0.0-rc.1 normalice a 1.0.0rc1 se confirma aquí, con la biblioteca de la CI.
    assert str(Version(semver)) == pep


def test_la_etiqueta_lleva_v_y_semver() -> None:
    assert v.etiqueta("1.0.0rc1") == "v1.0.0-rc.1"
    assert v.etiqueta("1.0.0") == "v1.0.0"
    assert v.etiqueta() == "v" + v.a_semver(_version_en_el_texto())


@pytest.mark.parametrize(
    "texto",
    ["1.0", "1.0.0.1", "v1.0.0", "1.0.0-rc1", "1.0.0rc", "uno", "", "1.0.0 ", "1.0.0rc1.post1"],
)
def test_una_version_que_no_es_pep440_ni_semver_se_rechaza(texto: str) -> None:
    with pytest.raises(ValueError, match="versión"):
        v.a_semver(texto)
    with pytest.raises(ValueError, match="versión"):
        v.a_pep440(texto)


@pytest.mark.parametrize("texto", ["1.0.0-rc.1", "1.0.0-alpha.2"])
def test_semver_no_pasa_como_pep440(texto: str) -> None:
    with pytest.raises(ValueError, match="versión"):
        v.a_semver(texto)


@pytest.mark.parametrize("texto", ["1.0.0rc1", "0.9.0a2"])
def test_pep440_no_pasa_como_semver(texto: str) -> None:
    with pytest.raises(ValueError, match="versión"):
        v.a_pep440(texto)


def test_siguiente_parche_es_mayor_que_la_candidata_y_que_la_final() -> None:
    assert v.siguiente_parche("1.0.0") == "1.0.1"
    assert v.siguiente_parche("1.0.0-rc.1") == "1.0.1"
    assert v.siguiente_parche("1.0.9") == "1.0.10"  # frontera: el parche no se trunca a un dígito
    assert Version("1.0.1") > Version("1.0.0-rc.1")
    assert Version("1.0.1") > Version("1.0.0")
    with pytest.raises(ValueError, match="versión"):
        v.siguiente_parche("1.0.0rc1")
