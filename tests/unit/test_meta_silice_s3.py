"""Parte S3 de la meta única de Sílice (spec S3 §13.6; plan 0.8.0, tarea 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_silice import FASES, fases_hasta, partes, validar_partes
from scripts.meta_silice_s3 import (
    PARES_S3,
    PARTE,
    PROTOCOLOS,
    REQUISITOS_S3_0,
    evaluar_cobertura_en_ci,
    evaluar_html_inseguro,
    evaluar_literal_of001,
    evaluar_protocolos,
    evaluar_ramas_sin_nucleo,
    huella_de,
)

RAIZ = Path(__file__).resolve().parents[2]


def test_la_parte_s3_se_descubre_y_sus_fases_existen_en_0_8_0() -> None:
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert FASES["0.8.0"] == ("S3-0", "S3-1", "S3-2", "S3-3", "S3-4", "S3-5", "S3-6", "S3-7")
    assert {par.fase for par in PARES_S3} <= set(FASES["0.8.0"])


def test_rf_100_solo_se_exige_con_la_fase_s3_6() -> None:
    assert "RF-100" not in PARTE.requisitos["S3-0"]
    assert PARTE.requisitos["S3-6"] == ("RF-100",)
    assert "S3-6" not in fases_hasta("0.8.0", "S3-5") and "S3-6" in fases_hasta("0.8.0", "S3-6")


def test_la_ers_de_s3_0_pide_cada_uc_rf_y_rnf_de_la_version() -> None:
    assert set(REQUISITOS_S3_0) == {f"UC-{n}" for n in (21, 22, 23)} | {
        f"RF-{n}" for n in range(80, 90)
    } | {"RNF-16", "RNF-17"}


def test_los_pares_nombran_archivos_del_repositorio_cuando_su_fase_ya_se_construyo() -> None:
    for par in PARES_S3:
        assert par.prueba.startswith("tests/") and "/" in par.implementacion


def test_los_pares_de_las_fases_ya_construidas_existen() -> None:
    """Ninguna fase de la 0.8.0 está construida mientras esta prueba solo vea S3-0."""
    for par in PARES_S3:
        if par.fase == "S3-0":
            assert (RAIZ / par.prueba).is_file(), par.prueba


# --- S3-M1: la huella de los protocolos -------------------------------------------------------


def _protocolos(tmp_path: Path, huellas_malas: tuple[str, ...] = ()) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    escritas = {}
    for relativa in PROTOCOLOS:
        ruta = tmp_path / relativa
        ruta.write_text(f"protocolo {relativa}", encoding="utf-8")
        escritas[relativa] = "0" * 64 if relativa in huellas_malas else huella_de(ruta)
    (docs / "protocolos_s3.json").write_text(json.dumps({"protocolos": escritas}), encoding="utf-8")
    return docs / "protocolos_s3.json"


def test_los_protocolos_con_su_huella_pasan(tmp_path: Path) -> None:
    huellas = _protocolos(tmp_path)
    assert evaluar_protocolos(tmp_path, huellas)[0] is Estado.OK


def test_un_protocolo_cambiado_despues_de_escribir_su_huella_falla(tmp_path: Path) -> None:
    huellas = _protocolos(tmp_path)
    (tmp_path / PROTOCOLOS[1]).write_text("otro texto", encoding="utf-8")
    estado, detalle = evaluar_protocolos(tmp_path, huellas)
    assert estado is Estado.FALLA and "protocolo_deteccion_planos" in detalle


def test_sin_el_archivo_de_huellas_o_sin_un_protocolo_falla(tmp_path: Path) -> None:
    assert evaluar_protocolos(tmp_path, tmp_path / "docs" / "protocolos_s3.json")[0] is Estado.FALLA
    huellas = _protocolos(tmp_path)
    (tmp_path / PROTOCOLOS[0]).unlink()
    assert evaluar_protocolos(tmp_path, huellas)[0] is Estado.FALLA


# --- S3-M2: el literal de OF-001 limpio -------------------------------------------------------


def test_el_literal_de_of001_limpio_exige_items_y_hallazgos(tmp_path: Path) -> None:
    ruta = tmp_path / "of001_limpio.py"
    assert evaluar_literal_of001(ruta)[0] is Estado.FALLA
    ruta.write_text('LIMPIO = {"dxf": {"items": (), "hallazgos": ()}}\n', encoding="utf-8")
    assert evaluar_literal_of001(ruta)[0] is Estado.FALLA
    ruta.write_text(
        'LIMPIO = {"dxf": {"items": (("a", "b", "c"),), "hallazgos": (("R8", "A", "d"),)}}\n',
        encoding="utf-8",
    )
    assert evaluar_literal_of001(ruta)[0] is Estado.OK


# --- S3-M3: ningún HTML inseguro --------------------------------------------------------------


def test_unsafe_allow_html_se_detecta_en_cualquier_carpeta_vigilada(tmp_path: Path) -> None:
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "ok.py").write_text("st.markdown('x')\n", encoding="utf-8")
    assert evaluar_html_inseguro(tmp_path, ("ui", "api"))[0] is Estado.OK
    (tmp_path / "ui" / "mal.py").write_text(
        "st.markdown(x, unsafe_allow_html=True)\n", encoding="utf-8"
    )
    estado, detalle = evaluar_html_inseguro(tmp_path, ("ui", "api"))
    assert estado is Estado.FALLA and "ui/mal.py" in detalle


# --- S3-M4: cobertura en la CI ----------------------------------------------------------------


@pytest.mark.parametrize(
    "texto,esperado",
    [
        (None, Estado.PENDIENTE),
        ('run: coverage report --include="core/*" --fail-under=80\n', Estado.FALLA),
        ('run: coverage report --include="seguridad/*,paquete/*" --fail-under=80\n', Estado.OK),
    ],
)
def test_la_cobertura_de_seguridad_y_paquete_se_exige_en_la_ci(texto, esperado) -> None:
    assert evaluar_cobertura_en_ci(texto)[0] is esperado


# --- S3-M5: las ramas de planos y anomalías no tocan core/ ------------------------------------


def test_las_ramas_sin_nucleo_dan_ok_solo_con_diffs_vacios() -> None:
    assert evaluar_ramas_sin_nucleo({})[0] is Estado.PENDIENTE
    assert evaluar_ramas_sin_nucleo({"Merge inc/080-s3-5-planos": None})[0] is Estado.PENDIENTE
    assert evaluar_ramas_sin_nucleo({"Merge inc/080-s3-5-planos": ""})[0] is Estado.OK
    estado, detalle = evaluar_ramas_sin_nucleo(
        {"Merge inc/080-s3-5-planos": "", "Merge inc/080-s3-6-anomalias": " core/x.py | 2 +-\n"}
    )
    assert estado is Estado.FALLA and "s3-6" in detalle
