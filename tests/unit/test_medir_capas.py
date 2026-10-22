"""Medición del Python autónomo y de las capas (spec S5 §1.3 y S5-0.3; PLAN_SILICE_100 T2).

Oráculos: sumas hechas a mano en cada caso (comentario al lado) y las cifras medidas que la
bitácora `docs/bitacora/2026-10-silice-100.md` (S5-0.3) dejó escritas. La 1.5 sumó el extra `pdf`
a la capa básica (commit 80c205a): `FIJAS` y `CAPAS` lo traen y aquí se exige.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from instalador import medir_capas as mc
from instalador.manifiesto import cargar

BASE = "alfa==1.0\nBeta_Uno==2.0 ; sys_platform == 'win32'\n"
API = BASE + "fastapi==0.115.0\nnumpy==2.3.0\n"
CIVIL = API + "ifcopenshell==0.8.1\nshapely==2.1.0\n"
ANOMALIAS = CIVIL + "scikit-learn==1.7.0\nnumpy==2.3.0\n"


def _capas(basica: float) -> dict[str, float]:
    """Capas de la básica con cifras redondas; solo cambia `basica` entre casos."""
    return {"basica": basica, "bcv": 1.0, "civil": 16.0, "anomalias": 26.0, "ia": 12.0, "pdf": 3.0}


def test_normalizar_une_guiones_guiones_bajos_y_puntos() -> None:
    assert mc.normalizar("Beta_Uno") == mc.normalizar("beta-uno") == "beta-uno"
    assert mc.normalizar("Zope.Interface") == "zope-interface"
    assert mc.normalizar("a__b--c..d") == "a-b-c-d"  # una racha de separadores es un solo guion


def test_paquetes_de_lee_nombre_y_version_y_salta_lo_demas() -> None:
    assert mc.paquetes_de(
        "# x\n-e .\nalfa==1.0\n    # via y\nBeta_Uno==2.0 ; python_version > '3'\ngamma>=3.0\n\n"
    ) == {
        "alfa": "1.0",
        "beta-uno": "2.0",
    }  # «gamma>=3.0» no es una versión fija: uv export --frozen nunca la escribe así
    assert mc.paquetes_de("") == {}


def test_cada_capa_trae_solo_lo_que_las_anteriores_no_tenian() -> None:
    capas = mc.capas_nuevas({"base": BASE, "api": API, "civil": CIVIL, "anomalias": ANOMALIAS})
    assert capas == {
        "base": {"alfa", "beta-uno"},
        "api": {"fastapi", "numpy"},
        "civil": {"ifcopenshell", "shapely"},
        "anomalias": {"scikit-learn"},  # numpy ya estaba en «api»
    }


def test_las_capas_medidas_son_las_del_manifiesto() -> None:
    """Lo que se mide (CAPAS acumuladas) es lo que el instalador básico lleva (manifiesto.toml)."""
    m = cargar()
    assert mc.FIJAS == ("basica", "bcv", "civil", "anomalias", "ia", "pdf")
    assert set(mc.CAPAS[mc.FIJAS[-1]]) == set(m.extras_basica)
    assert mc.CAPAS["similitud"] == [*mc.CAPAS[mc.FIJAS[-1]], *m.extras_similitud]
    assert mc.CAPAS["base"] == []
    # cada capa acumula la anterior y agrega exactamente un extra (o los cuatro de la básica)
    orden = ["basica", "bcv", "civil", "anomalias", "ia", "pdf", "similitud"]
    for anterior, siguiente in zip(orden, orden[1:], strict=False):
        assert mc.CAPAS[siguiente][:-1] == mc.CAPAS[anterior], siguiente
    assert mc.ORDEN_DE_RECORTE == ("civil", "anomalias")  # spec S5 §7.2


def test_el_tamano_de_un_paquete_se_suma_desde_su_record(tmp_path: Path) -> None:
    sitio = tmp_path / "site-packages"
    (sitio / "alfa").mkdir(parents=True)
    (sitio / "alfa" / "__init__.py").write_bytes(b"x" * 100)
    (sitio / "alfa" / "datos.bin").write_bytes(b"y" * 300)
    info = sitio / "alfa-1.0.dist-info"
    info.mkdir()
    (info / "RECORD").write_text(
        "alfa/__init__.py,sha256=abc,100\nalfa/datos.bin,sha256=def,300\n"
        "alfa-1.0.dist-info/RECORD,,\n../../Scripts/alfa.exe,,\nalfa/borrado.py,,\n",
        encoding="utf-8",
    )
    (info / "METADATA").write_text("Name: alfa\n", encoding="utf-8")
    # 100 + 300 = 400: ni RECORD, ni lo que sale de site-packages, ni lo que ya no está en disco
    assert mc.tamano_de_dist_info(sitio, info) == 400


def test_sin_record_el_paquete_no_suma(tmp_path: Path) -> None:
    info = tmp_path / "beta-2.0.dist-info"
    info.mkdir()
    assert mc.tamano_de_dist_info(tmp_path, info) == 0


def test_estimar_xz_comprime_lo_repetitivo_y_no_inventa_bytes(tmp_path: Path) -> None:
    repetitivo = tmp_path / "a.txt"
    repetitivo.write_bytes(b"silice " * 20000)  # 140 000 bytes
    aleatorio = tmp_path / "b.bin"
    aleatorio.write_bytes(random.Random(20261012).randbytes(20000))
    solo_repetitivo = mc.estimar_xz([repetitivo])
    assert 0 < solo_repetitivo < 140_000 // 20
    assert mc.estimar_xz([aleatorio]) > 20000 * 0.9  # lo incompresible no se achica
    assert mc.estimar_xz([]) > 0  # el contenedor vacío también ocupa algo
    assert mc.estimar_xz([repetitivo, aleatorio]) > mc.estimar_xz([aleatorio])


@pytest.mark.parametrize(
    ("basica", "esperado"),
    [
        (65.0, []),  # 20 + 7 + 65 + 1 + 16 + 26 + 12 + 3 = 150,00: cabe justo
        (65.01, ["civil"]),  # 150,01 > 150; sin civil: 134,01
        (81.0, ["civil"]),  # 166 - 16 = 150,00: cabe sin tocar anomalías
        (81.01, ["civil", "anomalias"]),  # 166,01 - 16 = 150,01; - 26 = 124,01
        (95.0, ["civil", "anomalias"]),  # 180 - 16 - 26 = 138
        (107.0, ["civil", "anomalias"]),  # 192 - 42 = 150,00: el máximo que todavía cabe
    ],
)
def test_el_recorte_sigue_el_orden_del_spec_primero_civil_y_luego_anomalias(
    basica: float, esperado: list[str]
) -> None:
    assert mc.decidir_recorte(20.0, _capas(basica)) == esperado


@pytest.mark.parametrize("basica", [107.01, 150.0])  # 192,01 - 42 = 150,01; 235 - 42 = 193
def test_si_ni_recortando_cabe_se_dice(basica: float) -> None:
    with pytest.raises(ValueError, match="150"):
        mc.decidir_recorte(20.0, _capas(basica))


def test_el_codigo_y_el_limite_se_pueden_cambiar() -> None:
    # 20 + 10 + 65 + 58 = 153 con 10 MB de código: ya no cabe sin civil (153 - 16 = 137)
    assert mc.decidir_recorte(20.0, _capas(65.0), codigo_mb=10.0) == ["civil"]
    assert mc.decidir_recorte(20.0, _capas(65.0), limite=149.99) == ["civil"]


def test_las_cifras_medidas_de_la_bitacora_no_piden_recorte() -> None:
    """S5-0.3: Python 15,4 + código 7,0 + base 19,9 + básica 45,8 + bcv 0,1 + civil 15,1 +
    anomalías 26,0 + ia 0,9 = 130,2 MB (la bitácora: «Recorte: ninguno»). El pdf de la 1.5 no se
    midió: cabe mientras pese menos que el margen de 19,8 MB."""
    capas = {
        "basica": 19.9 + 45.8,
        "bcv": 0.1,
        "civil": 15.1,
        "anomalias": 26.0,
        "ia": 0.9,
        "pdf": 19.79,  # 149,99
    }
    assert mc.decidir_recorte(15.4, capas) == []
    assert mc.decidir_recorte(15.4, {**capas, "pdf": 19.81}) == ["civil"]


def test_la_tabla_para_la_bitacora_trae_cada_capa_y_el_total() -> None:
    datos = {
        "python": {"instalado_mb": 70.0, "comprimido_mb": 15.0},
        "capas": {
            "basica": {"paquetes": 120, "instalado_mb": 348.0, "comprimido_mb": 62.0},
            "civil": {"paquetes": 3, "instalado_mb": 87.0, "comprimido_mb": 16.0},
        },
        "recorte": [],
    }
    tabla = mc.tabla_markdown(datos)
    assert "| Python autónomo | — | 70,0 | 15,0 |" in tabla
    assert "| basica | 120 | 348,0 | 62,0 |" in tabla and "| civil | 3 | 87,0 | 16,0 |" in tabla
    # 15 + 62 + 16 = 93
    assert "Total comprimido (estimado xz -9): 93,0 MB" in tabla and "Recorte: ninguno" in tabla
    con_recorte = mc.tabla_markdown({**datos, "recorte": ["civil", "anomalias"]})
    assert "Recorte: civil, anomalias." in con_recorte


def test_main_escribe_el_json_y_la_tabla_sin_medir_de_verdad(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    datos = {
        "python": {"version": "3.13.13", "instalado_mb": 62.4, "comprimido_mb": 15.4},
        "capas": {"basica": {"paquetes": 42, "instalado_mb": 231.2, "comprimido_mb": 45.8}},
        "recorte": [],
    }
    pedidas: list[str] = []
    monkeypatch.setattr(mc, "medir", lambda version: pedidas.append(version) or datos)
    salida = tmp_path / "capas.json"
    assert mc.main(["--salida", str(salida), "--tabla"]) == 0
    assert pedidas == [cargar().python]  # por defecto, la misma versión que el manifiesto (T13)
    assert json.loads(salida.read_text(encoding="utf-8")) == datos
    assert "| basica | 42 | 231,2 | 45,8 |" in capsys.readouterr().out


def test_ninguna_capa_medida_incluye_el_extra_ui_retirado() -> None:
    assert all("ui" not in extras for extras in mc.CAPAS.values())
