"""Los manuales dicen lo que S5 promete (spec S5 §10.5; RF-97, RF-98; T19).

Desviaciones registradas (bitácora 2026-10-silice-100, `inc/100-s5-4-humo`): la huella de la clave
del proyecto lleva la marca `PENDIENTE H1` mientras T3 no exista (`operacion/clave_proyecto.pub`);
las secciones nuevas del manual técnico son la 14 a la 16 (el plan decía 12 a 14, ya ocupadas).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CLAVE_PUBLICA = RAIZ / "operacion" / "clave_proyecto.pub"


def _leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8").replace("‑", "-")


SECCIONES = (
    "Requisitos",
    "Comprobar la huella y la firma",
    "Instalar",
    "Primer arranque",
    "Casos",
    "Red local",
    "API y claves",
    "Actualizar",
    "Respaldos",
    "Restaurar",
    "Desinstalar",
    "SmartScreen",
    "Problemas frecuentes",
)


def test_el_manual_de_instalacion_tiene_las_secciones_del_spec_en_orden() -> None:
    titulos = re.findall(r"^## (.+?)\s*$", _leer("docs/manual_instalacion.md"), re.M)
    assert titulos == list(SECCIONES)


def test_el_manual_dice_lo_que_el_spec_manda_decir() -> None:
    minusculas = _leer("docs/manual_instalacion.md").lower()
    faltan = [
        frase
        for frase in (
            "red de confianza",
            "WPA2",
            "cloudflared",
            "ngrok",
            "sin cifrar",
            "keyring",
            "no viaja en los respaldos",
            "%LOCALAPPDATA%\\Silice",
            "Windows protegió su PC",
            "SHA256SUMS",
            "SHA256SUMS.ed25519",
            "verificar_sumas.py",
            "operacion verificar-instalador",
            "base no adoptable",
            "versión más nueva",
            "puerto ocupado",
            "IP de la red local",
        )
        if frase.lower() not in minusculas
    ]
    assert faltan == []


def test_el_manual_trae_la_huella_de_la_clave_o_la_marca_de_pendiente() -> None:
    """Con la clave de T3 en el repositorio, su huella SHA-256 tiene que estar en el manual; sin
    ella (H1 pendiente de Eugenio), el manual lo dice con la marca `PENDIENTE H1`."""
    manual = _leer("docs/manual_instalacion.md")
    if CLAVE_PUBLICA.is_file():
        publica = bytes.fromhex(CLAVE_PUBLICA.read_text(encoding="utf-8").strip())
        assert hashlib.sha256(publica).hexdigest() in "".join(manual.split())
        assert "PENDIENTE H1" not in manual
    else:
        seccion = manual.split("## Comprobar la huella y la firma", 1)[1].split("\n## ", 1)[0]
        assert "PENDIENTE H1" in seccion


def test_el_manual_nombra_el_instalador_con_el_nombre_que_construye_construir() -> None:
    from instalador.construir import nombre_instalador

    manual = _leer("docs/manual_instalacion.md")
    basico = nombre_instalador("X.Y.Z", "basico").replace("X.Y.Z", "")
    completo = nombre_instalador("X.Y.Z", "completo").replace("X.Y.Z", "")
    assert basico.split(".exe")[0] in manual  # «Silice-»
    assert "-completo.exe" in manual and completo.endswith("-completo.exe")


def test_el_manual_de_usuario_empieza_por_el_instalador() -> None:
    manual = _leer("docs/manual_usuario.md")
    seccion1 = manual.split("## 2.", 1)[0]
    assert "Silice-" in seccion1 and "manual_instalacion.md" in seccion1
    assert "uv sync" not in seccion1  # el camino de desarrollo pasó al manual técnico


def test_el_manual_tecnico_explica_construir_la_cli_y_publicar() -> None:
    manual = _leer("docs/manual_tecnico.md")
    titulos = re.findall(r"^## (\d+)\. (.+?)\s*$", manual, re.M)
    por_titulo = {titulo: int(numero) for numero, titulo in titulos}
    for titulo in ("Construir el instalador", "La orden `operacion`", "Publicar una versión"):
        assert titulo in por_titulo, titulo
    assert [
        por_titulo[t]
        for t in ("Construir el instalador", "La orden `operacion`", "Publicar una versión")
    ] == [14, 15, 16]
    numeros = [int(n) for n, _ in titulos]
    assert numeros == sorted(numeros) and len(numeros) == len(set(numeros))  # sin repetir
    faltan = [
        dato
        for dato in (
            "instalador/construir.py",
            "SHA256SUMS",
            "firmar-sumas",
            "v1.0-tesis",
            "CHANGELOG.md",
        )
        if dato not in manual
    ]
    assert faltan == []


def test_el_camino_de_desarrollo_esta_en_el_manual_tecnico() -> None:
    entorno = _leer("docs/manual_tecnico.md").split("## 2.", 1)[1].split("\n## 3.", 1)[0]
    assert "### Instalación para desarrollo" in entorno and "uv sync" in entorno


def test_el_readme_tiene_los_dos_caminos_y_la_direccion_explicita() -> None:
    readme = _leer("README.md")
    assert "Silice-" in readme and "uv sync" in readme and "--server.address 127.0.0.1" in readme


def test_calidad_declara_rnf_19_y_la_ers_el_camino_del_instalador() -> None:
    calidad = _leer("docs/calidad_iso25010.md")
    assert "RNF-19" in calidad
    assert "cdnjs" not in calidad.split("## 7.", 1)[1].split("## 8.", 1)[0]


def test_el_indice_de_docs_enlaza_el_manual_de_instalacion() -> None:
    assert "manual_instalacion.md" in _leer("docs/README.md")
