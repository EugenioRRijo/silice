"""`instalador/verificar_sumas.py`: quien instala por primera vez no tiene Sílice (RP10-10)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from operacion import firma_sumas as fs

SCRIPT = Path(__file__).resolve().parents[2] / "instalador" / "verificar_sumas.py"


def _preparar(tmp_path: Path):
    privada = fs.generar_par()
    exe = tmp_path / "Silice-1.0.0.exe"
    exe.write_bytes(b"instalador")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({exe.name: hashlib.sha256(b"instalador").hexdigest()}))
    firma = tmp_path / "SHA256SUMS.ed25519"
    firma.write_bytes(fs.firmar(sumas.read_bytes(), privada))
    return exe, sumas, firma, fs.bytes_publicos(privada).hex()


def _correr(*argumentos: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *argumentos],
        capture_output=True,
        text=True,
        check=False,
    )


def test_el_script_independiente_verifica_con_la_clave_pasada_por_argumento(tmp_path: Path) -> None:
    exe, sumas, firma, publica = _preparar(tmp_path)
    resultado = _correr(str(exe), str(sumas), str(firma), "--publica", publica)
    assert resultado.returncode == 0 and "VERIFICADO" in resultado.stdout
    assert (
        hashlib.sha256(bytes.fromhex(publica)).hexdigest() in resultado.stdout
    )  # la huella a comparar


def test_el_script_independiente_rechaza_un_instalador_alterado_o_una_clave_ajena(
    tmp_path: Path,
) -> None:
    exe, sumas, firma, publica = _preparar(tmp_path)
    exe.write_bytes(b"alterado")
    assert _correr(str(exe), str(sumas), str(firma), "--publica", publica).returncode == 1
    exe.write_bytes(b"instalador")
    ajena = fs.bytes_publicos(fs.generar_par()).hex()
    resultado = _correr(str(exe), str(sumas), str(firma), "--publica", ajena)
    assert resultado.returncode == 1 and "NO INSTALE" in resultado.stderr


def test_el_script_independiente_no_importa_nada_de_silice() -> None:
    texto = SCRIPT.read_text(encoding="utf-8")
    assert "operacion" not in texto.replace("silice-sumas-v1", "")
    assert "import cryptography" in texto or "from cryptography" in texto
