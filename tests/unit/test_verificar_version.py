"""La etiqueta de git coincide con pyproject, normalizada (RF-99; spec S5 §9.2)."""

from __future__ import annotations

import subprocess
import sys

import pytest
from packaging.version import Version

from operacion import config
from scripts import verificar_version as vv


@pytest.mark.parametrize(
    ("etiqueta", "pep"),
    [
        ("v1.0.0", "1.0.0"),
        ("v1.0.0-rc.1", "1.0.0rc1"),
        ("v0.6.0", "0.6.0"),
        ("v0.9.0-alpha.2", "0.9.0a2"),
        ("v0.9.0-beta.3", "0.9.0b3"),
    ],
)
def test_etiqueta_que_coincide(etiqueta: str, pep: str) -> None:
    coincide, mensaje = vv.comparar(etiqueta, pep)
    assert coincide is True and "coincide" in mensaje and "no coincide" not in mensaje


@pytest.mark.parametrize(
    ("etiqueta", "pep", "razon"),
    [
        ("1.0.0", "1.0.0", "empezar con «v»"),
        ("V1.0.0", "1.0.0", "empezar con «v»"),
        ("v1.0.0", "1.0.1", "no coincide"),
        ("v1.0.0-rc.2", "1.0.0rc1", "no coincide"),
        ("v1.0.0-rc.1", "1.0.0", "no coincide"),
        ("v1.0", "1.0.0", "SemVer"),
        ("v1.0.0rc1", "1.0.0rc1", "SemVer"),
        ("v1.0.0-rc1", "1.0.0rc1", "SemVer"),
        ("v1.0.0-RC.1", "1.0.0rc1", "SemVer"),
    ],
)
def test_etiqueta_que_no_coincide(etiqueta: str, pep: str, razon: str) -> None:
    coincide, mensaje = vv.comparar(etiqueta, pep)
    assert coincide is False and razon in mensaje


def test_una_version_de_pyproject_invalida_no_coincide() -> None:
    coincide, mensaje = vv.comparar("v1.0.0", "no-es-version")
    assert coincide is False and "inválida" in mensaje


def test_main_devuelve_0_o_1(capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    monkeypatch.setattr(vv, "version_del_proyecto", lambda: "1.0.0rc1")
    assert vv.main(["--etiqueta", "v1.0.0-rc.1"]) == 0
    assert "coincide" in capsys.readouterr().out
    assert vv.main(["--etiqueta", "v1.0.0"]) == 1
    assert "no coincide" in capsys.readouterr().err


def test_imprimir_la_version_semver_y_la_de_parche(capsys, monkeypatch) -> None:
    monkeypatch.setattr(vv, "version_del_proyecto", lambda: "1.0.0rc1")
    assert vv.main(["--imprimir", "semver"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.0-rc.1"
    assert vv.main(["--imprimir", "parche"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.1"


def test_etiqueta_e_imprimir_son_excluyentes_y_uno_es_obligatorio(capsys) -> None:
    with pytest.raises(SystemExit) as salida:
        vv.main([])
    assert salida.value.code == 2
    with pytest.raises(SystemExit) as salida:
        vv.main(["--etiqueta", "v1.0.0", "--imprimir", "semver"])
    assert salida.value.code == 2
    capsys.readouterr()


def test_el_script_corre_solo_y_compara_con_el_pyproject_real() -> None:
    """Como lo llama la CI: `python scripts/verificar_version.py --etiqueta …` desde la raíz."""
    texto = (config.RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    pep = texto.split("[project]", 1)[1].split('version = "', 1)[1].split('"', 1)[0]
    script = str(config.RAIZ / "scripts" / "verificar_version.py")
    semver = subprocess.run(
        [sys.executable, script, "--imprimir", "semver"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=60,
    ).stdout.strip()
    bien = subprocess.run(
        [sys.executable, script, "--etiqueta", f"v{semver}"],
        capture_output=True,
        timeout=60,
        check=False,
    )
    mal = subprocess.run(
        [sys.executable, script, "--etiqueta", "v99.0.0"],
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert str(Version(semver)) == pep
    assert (bien.returncode, mal.returncode) == (0, 1)
