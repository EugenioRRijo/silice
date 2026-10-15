"""Firma Ed25519 de SHA256SUMS con la clave del proyecto (spec S5 §10.4; RV-16)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from operacion import firma_sumas as fs

CONTRASENA = "una contraseña larga y única 2026"


@pytest.fixture
def par():
    privada = fs.generar_par()
    return privada, fs.bytes_publicos(privada)


def test_la_firma_se_verifica_con_una_biblioteca_independiente(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"Silice-1.0.0.exe": "ab" * 32})
    firma = fs.firmar(sumas, privada)
    assert len(firma) == 64
    # el oráculo no pasa por nuestro `verificar`: la propia biblioteca, con el prefijo a mano
    Ed25519PublicKey.from_public_bytes(publica).verify(firma, b"silice-sumas-v1\0" + sumas)


def test_la_firma_lleva_separacion_de_dominio(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"Silice-1.0.0.exe": "ab" * 32})
    sin_prefijo = privada.sign(sumas)
    de_paquete = privada.sign(
        b"silice-paquete-v1\0" + sumas
    )  # el dominio del paquete auditado (S3)
    assert fs.verificar(sumas, sin_prefijo, publica) is False
    assert fs.verificar(sumas, de_paquete, publica) is False
    with pytest.raises(InvalidSignature):
        Ed25519PublicKey.from_public_bytes(publica).verify(
            sin_prefijo, b"silice-sumas-v1\0" + sumas
        )


def test_un_byte_cambiado_la_clave_equivocada_y_las_firmas_mal_formadas_no_verifican(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"a.exe": "cd" * 32})
    firma = fs.firmar(sumas, privada)
    assert fs.verificar(sumas, firma, publica) is True
    assert fs.verificar(sumas[:-1] + b"X", firma, publica) is False
    assert fs.verificar(sumas, firma, fs.bytes_publicos(fs.generar_par())) is False
    for rota in (b"", firma[:63], firma + b"\0", b"x" * 64):
        assert fs.verificar(sumas, rota, publica) is False
    assert fs.verificar(sumas, firma, b"corta") is False  # una pública que no mide 32 bytes


def test_sumas_con_crlf_no_verifican(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"a.exe": "cd" * 32, "b.exe": "ef" * 32})
    firma = fs.firmar(sumas, privada)
    assert fs.verificar(sumas.replace(b"\n", b"\r\n"), firma, publica) is False
    assert fs.verificar(b"\xef\xbb\xbf" + sumas, firma, publica) is False  # ni con BOM


def test_formatear_y_parsear_sumas_son_inversas_y_ordenan_por_nombre() -> None:
    entradas = {"z.exe": "11" * 32, "a.json": "22" * 32}
    crudo = fs.formatear_sumas(entradas)
    assert crudo == f"{'22' * 32}  a.json\n{'11' * 32}  z.exe\n".encode()
    assert fs.parsear_sumas(crudo) == entradas


def test_parsear_sumas_acepta_el_modo_binario_y_rechaza_lo_raro() -> None:
    ok = f"{'aa' * 32} *Silice.exe\n".encode()
    assert fs.parsear_sumas(ok) == {"Silice.exe": "aa" * 32}
    for malo in (
        b"no es una suma\n",
        f"{'AA' * 32}  mayusculas.exe\n".encode(),
        f"{'aa' * 32}  ../fuera.exe\n".encode(),
        f"{'aa' * 32}  a\\b.exe\n".encode(),
        f"{'aa' * 32}  a.exe\n{'bb' * 32}  a.exe\n".encode(),
        f"{'aa' * 32}  a.exe\r\n".encode(),
        f"{'aa' * 31}  corta.exe\n".encode(),
    ):
        with pytest.raises(ValueError):
            fs.parsear_sumas(malo)


def test_verificar_instalador_dice_la_causa(tmp_path: Path, par) -> None:
    privada, publica = par
    exe = tmp_path / "Silice-1.0.0.exe"
    exe.write_bytes(b"instalador")
    sumas = fs.formatear_sumas({exe.name: hashlib.sha256(b"instalador").hexdigest()})
    firma = fs.firmar(sumas, privada)
    ok, mensaje = fs.verificar_instalador(exe, sumas, firma, publica)
    assert ok is True and "VERIFICADO" in mensaje and fs.huella(publica) in mensaje

    exe.write_bytes(b"alterado")
    ok, mensaje = fs.verificar_instalador(exe, sumas, firma, publica)
    assert ok is False and "huella" in mensaje

    exe.write_bytes(b"instalador")
    otro = tmp_path / "Silice-9.9.9.exe"
    otro.write_bytes(b"x")
    assert "no figura" in fs.verificar_instalador(otro, sumas, firma, publica)[1]
    ok, mensaje = fs.verificar_instalador(exe, sumas, b"\0" * 64, publica)
    assert ok is False and "firma" in mensaje and "no instale" in mensaje
    ok, mensaje = fs.verificar_instalador(exe, b"basura", firma, publica)
    assert ok is False


def test_la_privada_se_guarda_cifrada_y_exige_la_contrasena(tmp_path: Path, par) -> None:
    privada, publica = par
    ruta = tmp_path / "clave_proyecto.enc"
    fs.guardar_privada(privada, CONTRASENA, ruta)
    crudo = ruta.read_bytes()
    semilla = privada.private_bytes_raw()
    assert semilla not in crudo and semilla.hex().encode() not in crudo
    datos = json.loads(crudo)
    assert datos["formato"] == "silice-clave-proyecto" and datos["publica"] == publica.hex()
    asimetrica = fs.cargar_privada(ruta, CONTRASENA)
    assert fs.bytes_publicos(asimetrica) == publica
    with pytest.raises(InvalidTag):
        fs.cargar_privada(ruta, "otra contraseña distinta 2026")


def test_una_contrasena_corta_se_rechaza(tmp_path: Path, par) -> None:
    with pytest.raises(ValueError, match="12"):
        fs.guardar_privada(par[0], "corta", tmp_path / "k.enc")


def test_la_clave_cifrada_no_se_puede_mover_a_otra_publica(tmp_path: Path, par) -> None:
    """El dato asociado liga el sobre a su clave pública: cambiar la pública a mano falla."""
    privada, _ = par
    ruta = tmp_path / "k.enc"
    fs.guardar_privada(privada, CONTRASENA, ruta)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["publica"] = fs.bytes_publicos(fs.generar_par()).hex()
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(InvalidTag):
        fs.cargar_privada(ruta, CONTRASENA)


def test_la_huella_es_el_sha256_de_la_clave_publica(par) -> None:
    _, publica = par
    assert fs.huella(publica) == hashlib.sha256(publica).hexdigest()
    agrupada = fs.huella_agrupada(publica)
    assert agrupada.replace(" ", "") == fs.huella(publica) and agrupada.count(" ") == 7


def test_leer_publica_acepta_hex_con_salto_de_linea_y_rechaza_lo_demas(tmp_path: Path, par) -> None:
    _, publica = par
    ruta = tmp_path / "clave_proyecto.pub"
    ruta.write_text(publica.hex() + "\n", encoding="utf-8")
    assert fs.leer_publica(ruta) == publica
    ruta.write_text("zz", encoding="utf-8")
    with pytest.raises(ValueError, match="clave pública"):
        fs.leer_publica(ruta)
    with pytest.raises(FileNotFoundError):
        fs.leer_publica(tmp_path / "no.pub")
