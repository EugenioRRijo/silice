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

NEUTRO = {
    "acento": None,
    "marco": None,
    "lateral": None,
    "complementario": None,
    "contador_numero": None,
    "contador_fondo": None,
    "tiene_logo": False,
    "avisos": [],
}
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
    b"\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00"
    b"\x00\x00\x00IEND\xaeB`\x82"
)
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"0" * 20
TOPE = 512 * 1024
TOPE_JSON = 64 * 1024


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
        json.dumps({"acento": "#ffffff", "marco": "#000000", "lateral": "#fafafa"}),
        encoding="utf-8",
    )
    assert cliente.get("/v1/tema").json() == {
        "acento": "#ffffff",
        "marco": "#000000",
        "lateral": "#fafafa",
        "complementario": None,
        "contador_numero": None,
        "contador_fondo": None,
        "tiene_logo": False,
        "avisos": [],
    }


def test_claves_nuevas_validas_se_devuelven_y_las_invalidas_se_descartan(
    tema: Path, cliente: TestClient
) -> None:
    (tema / "tema.json").write_text(
        json.dumps(
            {
                "complementario": "#123456",
                "contador_numero": "#654321",
                "contador_fondo": "azul",
            }
        ),
        encoding="utf-8",
    )
    cuerpo = cliente.get("/v1/tema").json()
    assert cuerpo["complementario"] == "#123456"
    assert cuerpo["contador_numero"] == "#654321"
    assert cuerpo["contador_fondo"] is None


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
    ("archivo", "tipo", "bytes_"),
    [("logo.jpg", "image/jpeg", JPEG), ("logo.webp", "image/webp", WEBP)],
)
def test_logo_jpg_y_webp_llevan_su_tipo(
    tema: Path, cliente: TestClient, archivo: str, tipo: str, bytes_: bytes
) -> None:
    (tema / archivo).write_bytes(bytes_)
    assert cliente.get("/v1/tema").json()["tiene_logo"] is True
    assert cliente.get("/v1/tema/logo").headers["content-type"] == tipo


def test_logo_svg_no_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    assert cliente.get("/v1/tema").json()["tiene_logo"] is False
    assert cliente.get("/v1/tema/logo").status_code == 404


def test_logo_mayor_de_512_kb_no_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.png").write_bytes(PNG_1X1 + b"0" * (TOPE + 1 - len(PNG_1X1)))
    assert cliente.get("/v1/tema").json()["tiene_logo"] is False
    assert cliente.get("/v1/tema/logo").status_code == 404


def test_logo_de_exactamente_512_kb_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.png").write_bytes(PNG_1X1 + b"0" * (TOPE - len(PNG_1X1)))
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


def test_json_muy_anidado_devuelve_neutro(tema: Path, cliente: TestClient) -> None:
    (tema / "tema.json").write_text("[" * 200000 + "]" * 200000, encoding="utf-8")
    respuesta = cliente.get("/v1/tema")
    assert respuesta.status_code == 200
    assert respuesta.json() == NEUTRO
    (tema / "tema.json").write_text(
        '{"acento": ' + "[" * 200000 + "]" * 200000 + "}", encoding="utf-8"
    )
    assert cliente.get("/v1/tema").json() == NEUTRO


def test_json_mayor_de_64_kb_devuelve_neutro(tema: Path, cliente: TestClient) -> None:
    relleno = " " * TOPE_JSON
    (tema / "tema.json").write_text('{"acento": "#123abc"}' + relleno, encoding="utf-8")
    assert cliente.get("/v1/tema").json() == NEUTRO


def test_json_de_exactamente_64_kb_se_lee(tema: Path, cliente: TestClient) -> None:
    base = '{"acento": "#123abc"}'
    (tema / "tema.json").write_text(base + " " * (TOPE_JSON - len(base)), encoding="utf-8")
    assert cliente.get("/v1/tema").json()["acento"] == "#123abc"


@pytest.mark.parametrize("archivo", ["logo.png", "logo.jpg", "logo.webp"])
def test_logo_cuyos_bytes_no_son_de_la_imagen_no_se_sirve(
    tema: Path, cliente: TestClient, archivo: str
) -> None:
    (tema / archivo).write_bytes(b"<html><script>alert(1)</script></html>")
    assert cliente.get("/v1/tema").json()["tiene_logo"] is False
    assert cliente.get("/v1/tema/logo").status_code == 404


def test_logo_con_firma_de_otro_formato_no_se_sirve(tema: Path, cliente: TestClient) -> None:
    (tema / "logo.png").write_bytes(JPEG)
    assert cliente.get("/v1/tema").json()["tiene_logo"] is False


def test_colores_sin_contraste_se_aplican_y_traen_avisos_exactos(
    tema: Path, cliente: TestClient
) -> None:
    """Marco y acento blancos, lateral negro: el tema se devuelve tal cual y con sus avisos.

    Oráculos a mano (WCAG 2.x; luminancia de #ffffff = 1, de #000000 = 0): blanco sobre blanco =
    1:1; #161616 (texto normal de Carbon g10, luminancia 0,0080) sobre negro = 1,16:1 -> «1,1».
    El borde #8d8d8d sobre blanco (3,3:1) y sobre negro (6,3:1) pasa. La raya del activo: el marco
    blanco sobre #e5e0df (luminancia 0,753) = 1,05 / 0,803 = 1,31:1 -> «1,3»; el número del
    contador, que sigue al marco, da lo mismo sobre ese fondo. El botón sigue al marco blanco:
    blanco sobre blanco 1,0; al pasar el ratón (#d9d9d9) 1,41 y al pulsar (#b3b3b3) 2,10 -> «2,0».
    """
    (tema / "tema.json").write_text(
        json.dumps({"acento": "#ffffff", "marco": "#ffffff", "lateral": "#000000"}),
        encoding="utf-8",
    )
    respuesta = cliente.get("/v1/tema")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "acento": "#ffffff",
        "marco": "#ffffff",
        "lateral": "#000000",
        "complementario": None,
        "contador_numero": None,
        "contador_fondo": None,
        "tiene_logo": False,
        "avisos": [
            "El texto de la barra superior no se lee bien sobre el color del marco:"
            " 1,0:1, hace falta 4,5:1",
            "El texto de los botones principales no se lee bien sobre su fondo:"
            " 1,0:1, hace falta 7:1",
            "El texto de los botones principales no se lee bien al pasar el ratón:"
            " 1,4:1, hace falta 7:1",
            "El texto de los botones principales no se lee bien al pulsarlos:"
            " 2,0:1, hace falta 7:1",
            "Las iniciales de la cuenta no se leen bien sobre el color de acento:"
            " 1,0:1, hace falta 4,5:1",
            "Los enlaces no se leen bien sobre el fondo de la página: 1,0:1, hace falta 4,5:1",
            "Los enlaces no se leen bien sobre las capas blancas: 1,0:1, hace falta 4,5:1",
            "El texto del menú lateral no se lee bien sobre el color lateral:"
            " 1,1:1, hace falta 4,5:1",
            "La raya de color de acento bajo la barra superior casi no se ve sobre el color"
            " del marco: 1,0:1, hace falta 3:1",
            "La raya del elemento activo del menú lateral casi no se ve sobre su fondo:"
            " 1,3:1, hace falta 3:1",
            "El contorno del contador casi no se ve sobre el fondo de la opción activa del menú"
            " lateral: 1,3:1, hace falta 3:1",
        ],
    }
