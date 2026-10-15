"""LICENCIAS\\: la de Python y la de cada paquete incluido (spec S5 §7.1 paso 5; P9; T14).

`licencias.py` se corre con el Python construido y solo biblioteca estándar: aquí se corre con
`-S` (sin `site`) sobre un `site-packages` sintético en `tmp_path`. La 1.5 (commit 80c205a) sumó
que todo lo de `*.dist-info/licenses/` (PEP 639) viaja, se llame como se llame (pypdfium2).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "instalador" / "licencias.py"


def _dist(
    sitio: Path,
    nombre: str,
    version: str,
    licencia: str | None,
    archivos: dict[str, str] | None = None,
    extra_meta: str = "",
) -> None:
    """Un paquete instalado: METADATA, RECORD y los archivos (ruta relativa a la dist-info)."""
    info = sitio / f"{nombre}-{version}.dist-info"
    info.mkdir(parents=True)
    meta = f"Metadata-Version: 2.1\nName: {nombre}\nVersion: {version}\n"
    if licencia:
        meta += f"License-Expression: {licencia}\n"
    (info / "METADATA").write_text(meta + extra_meta, encoding="utf-8")
    registro = [f"{info.name}/METADATA,,"]
    for relativa, texto in (archivos or {}).items():
        destino = info / relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        registro.append(f"{info.name}/{relativa},,")
    (info / "RECORD").write_text("\n".join(registro) + "\n", encoding="utf-8")


def _correr(sitio: Path, salida: Path, python_licencia: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-S",
            "-X",
            "utf8",
            str(SCRIPT),
            "--salida",
            str(salida),
            "--solo-ruta",
            str(sitio),
            "--python-licencia",
            str(python_licencia),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _psf(tmp_path: Path) -> Path:
    psf = tmp_path / "LICENSE.txt"
    psf.write_text("PSF", encoding="utf-8")
    return psf


def test_copia_la_licencia_de_cada_paquete_y_la_de_python(tmp_path: Path) -> None:
    sitio, salida = tmp_path / "sitio", tmp_path / "LICENCIAS"
    sitio.mkdir()
    _dist(sitio, "alfa", "1.0", "MIT", {"licenses/LICENSE": "Texto de la licencia de alfa\n"})
    _dist(sitio, "beta", "2.0", "Apache-2.0", {"licenses/LICENSE.txt": "Texto de beta\n"})
    resultado = _correr(sitio, salida, _psf(tmp_path))
    assert resultado.returncode == 0, resultado.stderr
    assert (salida / "Python" / "LICENSE.txt").read_text(encoding="utf-8") == "PSF"
    assert (salida / "alfa-1.0" / "LICENSE").read_text(encoding="utf-8") == (
        "Texto de la licencia de alfa\n"
    )
    assert (salida / "beta-2.0" / "LICENSE.txt").is_file()
    indice = (salida / "INDICE.md").read_text(encoding="utf-8")
    assert "| alfa | 1.0 | MIT |" in indice and "| beta | 2.0 | Apache-2.0 |" in indice
    # el índice lista exactamente los dos paquetes del sitio, en orden alfabético
    filas = [f for f in indice.splitlines() if f.startswith("| ") and not f.startswith("| Paq")]
    assert filas == ["| alfa | 1.0 | MIT |", "| beta | 2.0 | Apache-2.0 |"]


def test_todo_lo_de_licenses_viaja_aunque_no_se_llame_license(tmp_path: Path) -> None:
    """PEP 639 (pypdfium2, 1.5): `Apache-2.0.txt` y las licencias de lo que trae compilado."""
    sitio, salida = tmp_path / "sitio", tmp_path / "LICENCIAS"
    sitio.mkdir()
    _dist(
        sitio,
        "pdfium",
        "4.0",
        "Apache-2.0 OR BSD-3-Clause",
        {
            "licenses/Apache-2.0.txt": "apache",
            "licenses/BSD-3-Clause.txt": "bsd",
            "licenses/terceros/freetype.txt": "freetype",
            "README.md": "no es licencia",
        },
    )
    resultado = _correr(sitio, salida, _psf(tmp_path))
    assert resultado.returncode == 0, resultado.stderr
    copiados = sorted(p.name for p in (salida / "pdfium-4.0").iterdir())
    assert copiados == ["Apache-2.0.txt", "BSD-3-Clause.txt", "freetype.txt"]


def test_dos_textos_con_el_mismo_nombre_no_se_pisan(tmp_path: Path) -> None:
    sitio, salida = tmp_path / "sitio", tmp_path / "LICENCIAS"
    sitio.mkdir()
    _dist(sitio, "gamma", "3.0", "MIT", {"licenses/LICENSE": "uno", "licenses/sub/LICENSE": "dos"})
    assert _correr(sitio, salida, _psf(tmp_path)).returncode == 0
    textos = {p.read_text(encoding="utf-8") for p in (salida / "gamma-3.0").iterdir()}
    assert textos == {"uno", "dos"}


def test_sin_expresion_se_usa_el_clasificador(tmp_path: Path) -> None:
    sitio, salida = tmp_path / "sitio", tmp_path / "LICENCIAS"
    sitio.mkdir()
    _dist(
        sitio,
        "delta",
        "4.0",
        None,
        {"LICENSE": "texto"},
        extra_meta="License: UNKNOWN\nClassifier: License :: OSI Approved :: MIT License\n",
    )
    assert _correr(sitio, salida, _psf(tmp_path)).returncode == 0
    assert "| delta | 4.0 | MIT License |" in (salida / "INDICE.md").read_text(encoding="utf-8")


def test_solo_texto_sin_licencia_declarada_basta(tmp_path: Path) -> None:
    sitio, salida = tmp_path / "sitio", tmp_path / "LICENCIAS"
    sitio.mkdir()
    _dist(sitio, "epsilon", "5.0", None, {"COPYING": "GPL? no: solo texto"})
    resultado = _correr(sitio, salida, _psf(tmp_path))
    assert resultado.returncode == 0, resultado.stderr
    indice = (salida / "INDICE.md").read_text(encoding="utf-8")
    assert "| epsilon | 5.0 | ver texto |" in indice


def test_un_paquete_sin_licencia_ni_texto_hace_fallar(tmp_path: Path) -> None:
    sitio = tmp_path / "sitio"
    sitio.mkdir()
    _dist(sitio, "huerfano", "0.1", None, {"README.md": "sin licencia"})
    _dist(sitio, "alfa", "1.0", "MIT", {"licenses/LICENSE": "x"})
    resultado = _correr(sitio, tmp_path / "L", _psf(tmp_path))
    assert resultado.returncode == 1
    problemas = [linea for linea in resultado.stderr.splitlines() if linea.strip()]
    assert problemas == ["huerfano 0.1: sin licencia declarada ni texto de licencia"]


def test_sin_la_licencia_de_python_falla(tmp_path: Path) -> None:
    sitio = tmp_path / "sitio"
    sitio.mkdir()
    _dist(sitio, "alfa", "1.0", "MIT", {"licenses/LICENSE": "x"})
    resultado = _correr(sitio, tmp_path / "L", tmp_path / "no_existe.txt")
    assert resultado.returncode == 1 and "Python" in resultado.stderr
    assert not (tmp_path / "L" / "Python").exists()


def test_ifcopenshell_sin_texto_en_dist_info_no_falla(tmp_path: Path) -> None:
    """ARQ-2: ifcopenshell no tiene archivo de licencia en dist-info; no debe fallar."""
    sitio, salida = tmp_path / "sitio", tmp_path / "LICENCIAS"
    sitio.mkdir()
    _dist(sitio, "ifcopenshell", "0.8.5", "LGPL-3.0-or-later", {})
    resultado = _correr(sitio, salida, _psf(tmp_path))
    assert resultado.returncode == 0, resultado.stderr
    indice = (salida / "INDICE.md").read_text(encoding="utf-8")
    assert "| ifcopenshell | 0.8.5 | LGPL-3.0-or-later |" in indice
