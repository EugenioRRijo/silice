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
