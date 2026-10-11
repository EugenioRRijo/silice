import hashlib
import re
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[1] / "fixtures" / "bcv"


def _campos(seccion: str) -> dict[str, str]:
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8").split(f"## {seccion}")[1]
    texto = texto.split("\n## ")[0]
    return dict(re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", texto, re.MULTILINE))


def test_la_tasa_declara_archivo_bcv_huella_y_64_hojas():
    campos = _campos("Tasa")
    archivo = CARPETA / campos["Archivo"]
    assert campos["Dirección"].startswith("https://www.bcv.org.ve/")
    assert hashlib.sha256(archivo.read_bytes()).hexdigest() == campos["SHA-256"]
    assert campos["Hojas (N)"] == "64"  # antecedentes §6: 3T‑2026, 01‑07 a 30‑09
    assert archivo.stat().st_size <= 20 * 1024 * 1024


def test_la_transcripcion_trae_el_literal_verificado():
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8")
    assert re.search(r"\| 2026-10-01 \| 858\.02 \| 860\.18 \|", texto)


def test_el_inpc_declara_archivo_y_huella():
    campos = _campos("INPC")
    huella = hashlib.sha256((CARPETA / campos["Archivo"]).read_bytes()).hexdigest()
    assert huella == campos["SHA-256"]
