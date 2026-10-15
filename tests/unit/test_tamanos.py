"""Tamaño de los instaladores contra RNF-19 (spec S5 §4.3 y §7.2; RP10-6: 1 MB = 10^6 bytes; T14).

Oráculo: los límites literales de RNF-19 (150 MB el básico, 650 MB el completo) escritos aquí en
bytes, con la frontera exacta (límite pasa, límite + 1 byte falla).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from instalador import tamanos


@pytest.mark.parametrize(
    ("perfil", "bytes_", "ok"),
    [
        ("basico", 150_000_000, True),
        ("basico", 150_000_001, False),
        ("basico", 1, True),
        ("basico", 0, False),  # un .exe vacío no es un instalador
        ("completo", 650_000_000, True),
        ("completo", 650_000_001, False),
        ("completo", 0, False),
    ],
)
def test_el_limite_es_exacto(perfil: str, bytes_: int, ok: bool) -> None:
    assert tamanos.evaluar(perfil, bytes_)[0] is ok


def test_los_limites_son_los_de_rnf_19_en_megabytes_decimales() -> None:
    assert tamanos.MB == 1_000_000
    assert tamanos.LIMITES == {"basico": 150_000_000, "completo": 650_000_000}


def test_el_mensaje_dice_cuanto_pesa_y_si_cumple() -> None:
    assert tamanos.evaluar("basico", 125_700_000)[1] == "basico: 125.7 MB de 150 MB (cumple)"
    assert tamanos.evaluar("completo", 650_000_001)[1] == (
        "completo: 650.0 MB de 650 MB (NO cumple)"
    )


def test_un_perfil_desconocido_se_rechaza() -> None:
    with pytest.raises(ValueError, match="perfil"):
        tamanos.evaluar("gigante", 1)


def test_medir_lee_el_exe_de_la_version_y_deja_el_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", "abc123")  # sin llamar a git
    (tmp_path / "Silice-1.0.0-rc.1.exe").write_bytes(b"x" * 1234)
    (tmp_path / "Silice-1.0.0-rc.1-completo.exe").write_bytes(b"y" * 99)
    basico = tamanos.medir(tmp_path, "1.0.0-rc.1", "basico")
    completo = tamanos.medir(tmp_path, "1.0.0-rc.1", "completo")
    assert basico["bytes"] == 1234 and basico["limite"] == 150_000_000
    assert basico["archivo"] == "Silice-1.0.0-rc.1.exe" and basico["ok"] is True
    assert completo["bytes"] == 99 and completo["limite"] == 650_000_000
    assert completo["archivo"] == "Silice-1.0.0-rc.1-completo.exe"
    assert basico["commit"] == "abc123"


def test_main_escribe_el_json_y_sale_con_1_si_se_pasa(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    (tmp_path / "Silice-1.0.0.exe").write_bytes(b"x" * 10)
    salida = tmp_path / "tamanos-basico.json"
    argumentos = [
        "--perfil",
        "basico",
        "--carpeta",
        str(tmp_path),
        "--version",
        "1.0.0",
        "--salida",
        str(salida),
    ]
    assert tamanos.main(argumentos) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["ok"] is True and datos["perfil"] == "basico" and datos["version"] == "1.0.0"
    # un archivo disperso de 150 000 001 bytes: un byte sobre el límite, sin escribirlos todos
    with (tmp_path / "Silice-1.0.0.exe").open("r+b") as exe:
        exe.truncate(150_000_001)
    assert tamanos.main(argumentos) == 1
    assert json.loads(salida.read_text(encoding="utf-8"))["ok"] is False
    (tmp_path / "Silice-1.0.0.exe").unlink()  # no dejar 150 MB en la carpeta temporal


def test_sin_el_exe_es_un_error_claro(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Silice-9.9.9.exe"):
        tamanos.medir(tmp_path, "9.9.9", "basico")


def test_el_nombre_coincide_con_el_de_construir() -> None:
    from instalador import construir

    for version in ("1.0.0", "1.0.0-rc.1"):
        for perfil in ("basico", "completo"):
            assert tamanos._nombre(version, perfil) == construir.nombre_instalador(version, perfil)
