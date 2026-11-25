"""Manifiesto determinista de corrida de auditoría (Fase 1)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aplicacion import manifiesto_corrida as mc
from operacion.version import version

REGLAS_ESPERADAS = {
    "core/verification/reglas.py",
    "adapters/hoja_empresa/reglas.py",
    "adapters/hoja_empresa/reglas_calculo.py",
    "adapters/hoja_empresa/reglas_contexto.py",
    "adapters/hoja_empresa/umbrales.py",
    "adapters/vial/reglas.py",
    "adapters/vial/constantes.py",
    "aplicacion/causas_raiz.py",
}


def test_manifiesto_es_determinista_y_sin_reloj() -> None:
    primero = mc.manifiesto(
        version_libreoffice="LibreOffice 24.8.3.2",
        semilla=20261123,
        configuracion_regional="es-VE",
    )
    segundo = mc.manifiesto(
        version_libreoffice="LibreOffice 24.8.3.2",
        semilla=20261123,
        configuracion_regional="es-VE",
    )
    assert primero == segundo
    assert primero["version_silice"] == version()
    assert set(primero["reglas"]) == REGLAS_ESPERADAS
    assert len(primero["sha256"]) == 64
    assert primero["version_libreoffice"] == "LibreOffice 24.8.3.2"
    assert primero["semilla"] == 20261123
    assert primero["configuracion_regional"] == "es-VE"
    assert set(primero).isdisjoint({"fecha", "hora", "timestamp", "creado_en"})


def test_manifiesto_cambia_si_cambia_un_archivo_de_reglas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    regla_a = tmp_path / "reglas_a.py"
    regla_b = tmp_path / "reglas_b.py"
    regla_a.write_bytes(b"UMBRAL = 1\n")
    regla_b.write_bytes(b"UMBRAL = 2\n")
    monkeypatch.setattr(mc, "ARCHIVOS_REGLAS", (regla_a, regla_b))

    antes = mc.manifiesto(semilla=7)
    assert antes == mc.manifiesto(semilla=7)
    esperado_a = hashlib.sha256(b"UMBRAL = 1\n").hexdigest()
    assert esperado_a in antes["reglas"].values()

    regla_b.write_bytes(b"UMBRAL = 3\n")
    despues = mc.manifiesto(semilla=7)
    assert despues["reglas"] != antes["reglas"]
    assert despues["sha256"] != antes["sha256"]


def test_sha256_global_cambia_con_parametros_de_corrida(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    regla = tmp_path / "reglas.py"
    regla.write_bytes(b"X = 1\n")
    monkeypatch.setattr(mc, "ARCHIVOS_REGLAS", (regla,))

    base = mc.manifiesto()
    assert base["version_libreoffice"] is None
    assert base["semilla"] is None
    assert base["configuracion_regional"] == "es-VE"
    assert mc.manifiesto(semilla=1)["sha256"] != base["sha256"]
    assert mc.manifiesto(version_libreoffice="24.8")["sha256"] != base["sha256"]
    assert mc.manifiesto(configuracion_regional="en-US")["sha256"] != base["sha256"]


def test_huella_normaliza_crlf_a_lf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    con_crlf = tmp_path / "a.py"
    con_lf = tmp_path / "b.py"
    con_crlf.write_bytes(b"X = 1\r\nY = 2\r\n")
    con_lf.write_bytes(b"X = 1\nY = 2\n")
    esperado = hashlib.sha256(b"X = 1\nY = 2\n").hexdigest()

    monkeypatch.setattr(mc, "ARCHIVOS_REGLAS", (con_crlf,))
    assert list(mc.manifiesto()["reglas"].values()) == [esperado]
    monkeypatch.setattr(mc, "ARCHIVOS_REGLAS", (con_lf,))
    assert list(mc.manifiesto()["reglas"].values()) == [esperado]


def test_umbrales_estan_en_los_archivos_de_reglas() -> None:
    assert mc.RAIZ / "adapters" / "hoja_empresa" / "umbrales.py" in mc.ARCHIVOS_REGLAS


def test_huellas_coinciden_con_la_etiqueta_de_reglas_congeladas() -> None:
    import re
    import subprocess

    etiqueta = "reglas-congeladas-2026-11-24"
    salida = subprocess.run(
        ["git", "show", etiqueta, "--no-patch"],
        cwd=mc.RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    if salida.returncode != 0:
        pytest.skip("La etiqueta de reglas congeladas no existe en este clon.")
    sellos = dict(
        (ruta, huella)
        for huella, ruta in re.findall(r"^([0-9a-f]{64})  (\S+\.py)$", salida.stdout, re.M)
    )
    assert sellos, "No se leyeron huellas de la etiqueta."
    huellas = mc.manifiesto()["reglas"]
    assert set(sellos) == set(huellas)
    # Solo se exige igualdad en los archivos que no cambiaron después de la etiqueta.
    for ruta, huella in sellos.items():
        cambiado = subprocess.run(
            ["git", "diff", "--quiet", etiqueta, "--", ruta], cwd=mc.RAIZ, check=False
        )
        if cambiado.returncode == 0:
            assert huellas[ruta] == huella, ruta
