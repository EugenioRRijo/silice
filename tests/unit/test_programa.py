"""manifiesto.json del programa instalado y `verificar-programa` (spec S5 §10.4 y §11.2; T13).

Oráculo: la huella SHA-256 se calcula aquí con `hashlib` sobre los bytes escritos por la prueba, y
las diferencias esperadas son las que la prueba siembra (una por clase: distinto, falta, sobra).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from operacion import __main__ as cli
from operacion import config, programa


@pytest.fixture
def app(tmp_path: Path) -> Path:
    (tmp_path / "codigo" / "ui").mkdir(parents=True)
    (tmp_path / "python").mkdir()
    # bytes, no texto: en Windows `write_text` cambiaría el salto de línea y el tamaño
    (tmp_path / "codigo" / "ui" / "app.py").write_bytes(b"print('hola')\n")
    (tmp_path / "codigo" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "python" / "python.exe").write_bytes(b"MZ fake")
    programa.escribir(
        tmp_path, ["codigo/ui/app.py", "codigo/pyproject.toml", "python/python.exe"], "1.0.0"
    )
    return tmp_path


def test_el_manifiesto_lista_cada_archivo_con_ruta_tamano_y_huella(app: Path) -> None:
    datos = json.loads((app / "manifiesto.json").read_text(encoding="utf-8"))
    assert datos["formato"] == "silice-manifiesto" and datos["version"] == "1.0.0"
    por_ruta = {a["ruta"]: a for a in datos["archivos"]}
    assert (
        list(por_ruta)
        == sorted(por_ruta)
        == [
            "codigo/pyproject.toml",
            "codigo/ui/app.py",
            "python/python.exe",
        ]
    )
    contenido = b"print('hola')\n"  # 14 bytes, los que escribió la fixture
    assert por_ruta["codigo/ui/app.py"] == {
        "ruta": "codigo/ui/app.py",
        "tamano": 14,
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }
    assert por_ruta["python/python.exe"]["tamano"] == 7


def test_las_rutas_se_escriben_con_barra_y_sin_repetir(tmp_path: Path) -> None:
    (tmp_path / "codigo" / "ui").mkdir(parents=True)
    (tmp_path / "codigo" / "ui" / "app.py").write_bytes(b"x")
    programa.escribir(tmp_path, [Path("codigo") / "ui" / "app.py", "codigo/ui/app.py"], "1.0.0")
    assert [a["ruta"] for a in programa.leer(tmp_path)["archivos"]] == ["codigo/ui/app.py"]


def test_un_programa_intacto_no_tiene_diferencias(app: Path) -> None:
    assert programa.verificar(app) == []


def test_verificar_detecta_distinto_falta_y_sobra(app: Path) -> None:
    (app / "codigo" / "ui" / "app.py").write_text("print('otro')\n", encoding="utf-8")
    (app / "python" / "python.exe").unlink()
    (app / "codigo" / "extra.py").write_text("x = 1\n", encoding="utf-8")
    assert programa.verificar(app) == [
        "distinto codigo/ui/app.py",
        "falta python/python.exe",
        "sobra codigo/extra.py",
    ]


def test_el_mismo_tamano_con_otro_contenido_es_distinto(app: Path) -> None:
    (app / "codigo" / "ui" / "app.py").write_bytes(b"print('HOLA')\n")  # 14 bytes
    assert programa.verificar(app) == ["distinto codigo/ui/app.py"]


def test_lo_que_sobra_fuera_de_codigo_no_cuenta(app: Path) -> None:
    """Solo `codigo\\` se compara entero: `python\\` y la raíz de `{app}` pueden tener más."""
    (app / "python" / "otro.dll").write_bytes(b"dll")
    (app / "unins000.exe").write_bytes(b"MZ")
    assert programa.verificar(app) == []


def test_sin_manifiesto_no_es_una_instalacion(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        programa.verificar(tmp_path)


def test_un_json_que_no_es_de_silice_se_rechaza(tmp_path: Path) -> None:
    (tmp_path / "manifiesto.json").write_text('{"formato": "otro"}', encoding="utf-8")
    with pytest.raises(ValueError, match="no es un manifiesto de Sílice"):
        programa.verificar(tmp_path)


def test_la_orden_verificar_programa(app: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(config, "RAIZ", app / "codigo")
    assert cli.main(["verificar-programa"]) == 0 and "coincide" in capsys.readouterr().out
    (app / "codigo" / "pyproject.toml").write_text("alterado", encoding="utf-8")
    assert cli.main(["verificar-programa"]) == 1
    assert "distinto codigo/pyproject.toml" in capsys.readouterr().err


def test_la_orden_verificar_programa_en_desarrollo_lo_dice(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(config, "RAIZ", tmp_path / "codigo")
    assert cli.main(["verificar-programa"]) == 1
    assert "no es una instalación" in capsys.readouterr().err.lower()
