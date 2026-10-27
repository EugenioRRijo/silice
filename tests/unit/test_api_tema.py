"""`GET /v1/tema` y `GET /v1/tema/logo`: el tema de la empresa, leído de `<datos>/tema/`.

Rutas públicas (la pantalla de entrada pinta antes de que haya sesión). El repositorio lleva tema
neutro: los valores reales viven fuera de él. Todo valor de estas pruebas es inventado.

Oráculos a mano: el cuerpo neutro, los tipos de imagen y el tope de 512 KB se escriben aquí; un
archivo roto, un color que no es `#rrggbb`, un logo de más de 512 KB o un SVG nunca tumban la ruta:
cae al tema neutro.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from operacion import config
from tests.fixtures.sesion_web import cliente as cliente_de

NEUTRO = {"acento": None, "marco": None, "lateral": None, "tiene_logo": False}
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
    b"\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00"
    b"\x00\x00\x00IEND\xaeB`\x82"
)
TOPE = 512 * 1024


@pytest.fixture
def tema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(config.VARIABLE_DATOS, str(tmp_path))
    carpeta = tmp_path / "tema"
    carpeta.mkdir()
    return carpeta


@pytest.fixture
def cliente() -> TestClient:
    return cliente_de(app)


def test_sin_carpeta_de_tema_devuelve_neutro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cliente: TestClient
) -> None:
    monkeypatch.setenv(config.VARIABLE_DATOS, str(tmp_path))
    respuesta = cliente.get("/v1/tema")
    assert respuesta.status_code == 200
    assert respuesta.json() == NEUTRO


def test_colores_validos_se_devuelven(tema: Path, cliente: TestClient) -> None:
    (tema / "tema.json").write_text(
        json.dumps({"acento": "#123abc", "marco": "#000000", "lateral": "#fafafa"}),
        encoding="utf-8",
    )
    assert cliente.get("/v1/tema").json() == {
        "acento": "#123abc",
        "marco": "#000000",
        "lateral": "#fafafa",
        "tiene_logo": False,
    }


def test_color_invalido_se_descarta(tema: Path, cliente: TestClient) -> None:
    (tema / "tema.json").write_text(
        json.dumps({"acento": "amarillo", "marco": "#12345", "lateral": 7}), encoding="utf-8"
    )
    respuesta = cliente.get("/v1/tema")
    assert respuesta.status_code == 200
    assert respuesta.json() == NEUTRO


@pytest.mark.parametrize("contenido", ["{no", "[1, 2]", '"texto"', ""])
def test_json_roto_devuelve_neutro(tema: Path, cliente: TestClient, contenido: str) -> None:
    (tema / "tema.json").write_text(contenido, encoding="utf-8")
    respuesta = cliente.get("/v1/tema")
    assert respuesta.status_code == 200
    assert respuesta.json() == NEUTRO


def test_json_no_utf8_devuelve_neutro(tema: Path, cliente: TestClient) -> None:
    (tema / "tema.json").write_bytes(b"\xff\xfe{\x00")
    assert cliente.get("/v1/tema").json() == NEUTRO


def test_logo_png_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.png").write_bytes(PNG_1X1)
    assert cliente.get("/v1/tema").json()["tiene_logo"] is True
    respuesta = cliente.get("/v1/tema/logo")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert respuesta.content == PNG_1X1


@pytest.mark.parametrize(
    ("archivo", "tipo"), [("logo.jpg", "image/jpeg"), ("logo.webp", "image/webp")]
)
def test_logo_jpg_y_webp_llevan_su_tipo(
    tema: Path, cliente: TestClient, archivo: str, tipo: str
) -> None:
    (tema / archivo).write_bytes(b"bytes de imagen")
    assert cliente.get("/v1/tema").json()["tiene_logo"] is True
    assert cliente.get("/v1/tema/logo").headers["content-type"] == tipo


def test_logo_svg_no_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    assert cliente.get("/v1/tema").json()["tiene_logo"] is False
    assert cliente.get("/v1/tema/logo").status_code == 404


def test_logo_mayor_de_512_kb_no_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.png").write_bytes(b"0" * (TOPE + 1))
    assert cliente.get("/v1/tema").json()["tiene_logo"] is False
    assert cliente.get("/v1/tema/logo").status_code == 404


def test_logo_de_exactamente_512_kb_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.png").write_bytes(b"0" * TOPE)
    assert cliente.get("/v1/tema").json()["tiene_logo"] is True


def test_sin_logo_el_logo_es_404(tema: Path, cliente: TestClient) -> None:
    respuesta = cliente.get("/v1/tema/logo")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No hay logo."}


def test_logo_que_es_una_carpeta_no_tumba_nada(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.png").mkdir()
    assert cliente.get("/v1/tema").json()["tiene_logo"] is False
    assert cliente.get("/v1/tema/logo").status_code == 404


def test_tema_sin_sesion(tema: Path, cliente: TestClient) -> None:
    assert not cliente.cookies
    assert cliente.get("/v1/tema").status_code == 200
