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


# SHA-256 (contenido con finales LF) sellados en la etiqueta git `reglas-congeladas-2026-11-24`.
# Se fijan aquí para no depender de que la etiqueta exista en el clon (sin pruebas omitidas).
SELLOS_ETIQUETA = {
    "core/verification/reglas.py": (
        "e4fb1579d25e38dcdb3348a4f4b01fd253ca404dc5b24f0a5f0586341ba8f8c2"
    ),
    "adapters/hoja_empresa/reglas.py": (
        "ff620d51f00aef7998ebd0bdcff21cd5f0b1e9a28a00a07e4d6032eff06cf8c1"
    ),
    "adapters/hoja_empresa/reglas_calculo.py": (
        "0231d006f015a9c76e77a0f6df3da4a9aacd2bc36abe0760b08b5b786aa57a54"
    ),
    "adapters/hoja_empresa/reglas_contexto.py": (
        "c938aa19cf754bed3003cc7788a8eed18b93e40859e0cb22379e22e0ef09b57b"
    ),
    "adapters/hoja_empresa/umbrales.py": (
        "a8da53e3cf0138b9b97a6e411d888d9ca8db7576cd6f28d16f44f15addc4df9d"
    ),
    "adapters/vial/reglas.py": ("531eb72cbcef5718e1d72b4d1b5656e651263869c9ddb30c7dc47ff1264c6961"),
    "adapters/vial/constantes.py": (
        "ebb5c6e586cf63a617e417e158c04165f2d1d52154f4aaeb4005aa4c0fff512b"
    ),
    "aplicacion/causas_raiz.py": (
        "bb2a53a4d13c8cc6aff3a84cd9669974ac49e7f8e547411ef55b3722a5f0c9d6"
    ),
}


def test_huellas_coinciden_con_las_selladas_en_la_etiqueta_de_reglas_congeladas() -> None:
    assert mc.manifiesto()["reglas"] == SELLOS_ETIQUETA
