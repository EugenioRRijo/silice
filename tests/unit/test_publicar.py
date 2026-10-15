"""Reunir, comprobar y firmar el SHA256SUMS único del release (RP10-9; spec S5 §10.4)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from instalador import publicar
from operacion import firma_sumas


def _carpeta(base: Path, perfil: str, contenido: bytes, sufijo: str) -> Path:
    carpeta = base / perfil
    carpeta.mkdir()
    exe = carpeta / f"Silice-1.0.0{sufijo}.exe"
    exe.write_bytes(contenido)
    (carpeta / "manifiesto.json").write_bytes(b'{"formato": "silice-manifiesto"}')
    (carpeta / f"pip-audit-{perfil}.json").write_bytes(b"{}")
    sumas = carpeta / f"SHA256SUMS-{perfil}"
    entradas = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in carpeta.iterdir()}
    sumas.write_bytes(firma_sumas.formatear_sumas(entradas))
    return carpeta


@pytest.fixture
def carpetas(tmp_path: Path) -> list[Path]:
    return [
        _carpeta(tmp_path, "basico", b"basico" * 100, ""),
        _carpeta(tmp_path, "completo", b"completo" * 100, "-completo"),
    ]


def test_reunir_arma_un_solo_sha256sums_ordenado_y_solo_con_lf(carpetas, tmp_path: Path) -> None:
    salida = tmp_path / "release"
    sumas = publicar.reunir(carpetas, salida)
    crudo = sumas.read_bytes()
    assert sumas == salida / "SHA256SUMS" and b"\r" not in crudo and crudo.endswith(b"\n")
    lineas = crudo.decode().splitlines()
    nombres = [linea.split("  ", 1)[1] for linea in lineas]
    assert nombres == sorted(nombres)
    assert "Silice-1.0.0.exe" in nombres and "Silice-1.0.0-completo.exe" in nombres
    assert "pip-audit-basico.json" in nombres and "pip-audit-completo.json" in nombres
    assert nombres.count("manifiesto.json") == 1  # el mismo para los dos perfiles
    assert (salida / "Silice-1.0.0.exe").exists()  # los archivos se copian junto a las sumas


def test_dos_manifiestos_distintos_son_un_error(carpetas, tmp_path: Path) -> None:
    (carpetas[1] / "manifiesto.json").write_bytes(b"otro")
    with pytest.raises(ValueError, match="manifiesto.json"):
        publicar.reunir(carpetas, tmp_path / "release")


def test_comprobar_contra_ci_detecta_un_archivo_cambiado_en_el_camino(
    carpetas, tmp_path: Path
) -> None:
    assert publicar.comprobar_contra_ci(carpetas) == []
    (carpetas[0] / "Silice-1.0.0.exe").write_bytes(b"alterado")
    problemas = publicar.comprobar_contra_ci(carpetas)
    assert problemas and "Silice-1.0.0.exe" in problemas[0]


def test_el_sha256sums_reunido_se_firma_y_verifica(carpetas, tmp_path: Path) -> None:
    sumas = publicar.reunir(carpetas, tmp_path / "release")
    privada = Ed25519PrivateKey.generate()
    publica = firma_sumas.bytes_publicos(privada)
    firma = firma_sumas.firmar(sumas.read_bytes(), privada)
    exe = tmp_path / "release" / "Silice-1.0.0.exe"
    assert firma_sumas.verificar_instalador(exe, sumas.read_bytes(), firma, publica)[0] is True


def test_un_sha256sums_guardado_con_crlf_ya_no_verifica(carpetas, tmp_path: Path) -> None:
    sumas = publicar.reunir(carpetas, tmp_path / "release")
    privada = Ed25519PrivateKey.generate()
    publica = firma_sumas.bytes_publicos(privada)
    firma = firma_sumas.firmar(sumas.read_bytes(), privada)
    con_crlf = sumas.read_bytes().replace(b"\n", b"\r\n")
    exe = tmp_path / "release" / "Silice-1.0.0.exe"
    assert firma_sumas.verificar_instalador(exe, con_crlf, firma, publica)[0] is False


@pytest.mark.parametrize(
    ("archivos", "ofensores"),
    [
        (["pyproject.toml", "uv.lock", "CHANGELOG.md", "docs/plan_pruebas.md", "README.md"], []),
        (["docs/bitacora/2026-10-silice-100.md"], []),
        (["core/budget/persistencia.py"], ["core/budget/persistencia.py"]),
        (["ui/app.py", "pyproject.toml"], ["ui/app.py"]),
        (["instalador/silice.iss"], ["instalador/silice.iss"]),
    ],
)
def test_entre_la_rc_y_v1_0_0_solo_cambian_version_changelog_y_documentos(
    archivos, ofensores
) -> None:
    assert publicar.cambios_permitidos(archivos) == ofensores
