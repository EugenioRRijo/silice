"""Las órdenes de la clave del proyecto (spec S5 §10.4)."""

from __future__ import annotations

import getpass
import hashlib

import pytest

from operacion import __main__ as cli
from operacion import config
from operacion import firma_sumas as fs

CONTRASENA = "una contraseña larga y única 2026"


@pytest.fixture
def contrasena(monkeypatch):
    monkeypatch.setattr(getpass, "getpass", lambda texto="": CONTRASENA)


def test_generar_clave_proyecto_escribe_la_cifrada_y_la_publica(
    tmp_path, contrasena, capsys
) -> None:
    carpeta = tmp_path / "fuera" / ".silice-clave"
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 0
    publica = fs.leer_publica(carpeta / "clave_proyecto.pub")
    assert (
        fs.bytes_publicos(fs.cargar_privada(carpeta / "clave_proyecto.enc", CONTRASENA)) == publica
    )
    salida = capsys.readouterr().out
    assert (
        publica.hex() in salida
        and fs.huella(publica) in salida
        and "operacion/clave_proyecto.pub" in salida
    )


@pytest.mark.parametrize(("donde", "palabra"), [("repo", "repositorio"), ("onedrive", "OneDrive")])
def test_generar_rechaza_el_repositorio_y_onedrive(
    tmp_path, contrasena, capsys, donde, palabra
) -> None:
    malo = (
        config.RAIZ / "secretos_de_prueba"
        if donde == "repo"
        else tmp_path / "OneDrive - Personal" / "claves"
    )
    assert cli.main(["generar-clave-proyecto", "--salida", str(malo)]) == 1
    assert palabra in capsys.readouterr().err and not malo.exists()


def test_generar_no_pisa_una_clave_existente(tmp_path, contrasena) -> None:
    carpeta = tmp_path / "k"
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 0
    antes = (carpeta / "clave_proyecto.enc").read_bytes()
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 1
    assert (carpeta / "clave_proyecto.enc").read_bytes() == antes


def test_firmar_sumas_escribe_la_firma_y_la_comprueba_contra_la_publica_del_programa(
    tmp_path, contrasena, monkeypatch
) -> None:
    carpeta = tmp_path / "k"
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 0
    monkeypatch.setattr(fs, "RUTA_PUBLICA", carpeta / "clave_proyecto.pub")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({"a.exe": "ab" * 32}))
    assert cli.main(["firmar-sumas", str(sumas), "--clave", str(carpeta)]) == 0
    firma = (tmp_path / "SHA256SUMS.ed25519").read_bytes()
    assert fs.verificar(sumas.read_bytes(), firma, fs.leer_publica(carpeta / "clave_proyecto.pub"))


def test_firmar_con_una_clave_que_no_es_la_del_programa_se_rechaza(
    tmp_path, contrasena, monkeypatch, capsys
) -> None:
    ajena, propia = tmp_path / "ajena", tmp_path / "propia"
    cli.main(["generar-clave-proyecto", "--salida", str(ajena)])
    cli.main(["generar-clave-proyecto", "--salida", str(propia)])
    monkeypatch.setattr(fs, "RUTA_PUBLICA", propia / "clave_proyecto.pub")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({"a.exe": "ab" * 32}))
    assert cli.main(["firmar-sumas", str(sumas), "--clave", str(ajena)]) == 1
    assert not (tmp_path / "SHA256SUMS.ed25519").exists()
    assert "clave del proyecto" in capsys.readouterr().err


def test_firmar_con_la_contrasena_equivocada_no_deja_traza(tmp_path, monkeypatch, capsys) -> None:
    carpeta = tmp_path / "k"
    monkeypatch.setattr(getpass, "getpass", lambda texto="": CONTRASENA)
    cli.main(["generar-clave-proyecto", "--salida", str(carpeta)])
    monkeypatch.setattr(getpass, "getpass", lambda texto="": "otra contraseña distinta 2026")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(b"")
    assert cli.main(["firmar-sumas", str(sumas), "--clave", str(carpeta)]) == 1
    error = capsys.readouterr().err
    assert "contraseña" in error.lower() and "Traceback" not in error


def test_verificar_instalador_acepta_y_rechaza(tmp_path, contrasena, capsys) -> None:
    carpeta = tmp_path / "k"
    cli.main(["generar-clave-proyecto", "--salida", str(carpeta)])
    privada = fs.cargar_privada(carpeta / "clave_proyecto.enc", CONTRASENA)
    exe = tmp_path / "Silice-1.0.0.exe"
    exe.write_bytes(b"instalador")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({exe.name: hashlib.sha256(b"instalador").hexdigest()}))
    (tmp_path / "SHA256SUMS.ed25519").write_bytes(fs.firmar(sumas.read_bytes(), privada))
    publica = fs.bytes_publicos(privada).hex()
    argumentos = [
        "verificar-instalador",
        str(exe),
        str(sumas),
        str(tmp_path / "SHA256SUMS.ed25519"),
        "--publica",
        publica,
    ]
    assert cli.main(argumentos) == 0 and "VERIFICADO" in capsys.readouterr().out
    exe.write_bytes(b"alterado")
    assert cli.main(argumentos) == 1 and "huella" in capsys.readouterr().err


def test_verificar_instalador_sin_clave_en_el_programa_lo_dice(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(fs, "RUTA_PUBLICA", tmp_path / "no_esta.pub")
    archivo = tmp_path / "x"
    archivo.write_bytes(b"x")
    assert cli.main(["verificar-instalador", str(archivo), str(archivo), str(archivo)]) == 1
    assert "clave del proyecto" in capsys.readouterr().err


def test_huella_clave_proyecto_imprime_el_sha256(tmp_path, monkeypatch, capsys) -> None:
    privada = fs.generar_par()
    ruta = tmp_path / "clave_proyecto.pub"
    ruta.write_text(fs.bytes_publicos(privada).hex() + "\n", encoding="utf-8")
    monkeypatch.setattr(fs, "RUTA_PUBLICA", ruta)
    assert cli.main(["huella-clave-proyecto"]) == 0
    assert fs.huella(fs.bytes_publicos(privada)) in capsys.readouterr().out
