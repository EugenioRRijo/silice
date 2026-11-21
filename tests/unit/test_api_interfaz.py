"""La interfaz nueva servida por el FastAPI en `/app` (RT-2, RF-112, RNF-22).

Se ejerce `api.main.app` real con una carpeta `dist` falsa en `tmp_path` (se parchea
`api.interfaz.DIST`): ninguna prueba depende de que `npm run build` haya corrido. La CSP esperada
es el literal del plan de la sesión 2 (Task 2.3a), escrito aquí a mano.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import interfaz
from api.main import app
from operacion import config
from operacion.base_datos import Destino, preparar_base
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)
MENSAJE_SIN_COMPILAR = "La interfaz nueva no está compilada (npm run build en frontend-desktop)."
INDICE = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Sílice</title>'
    '<script type="module" src="/app/assets/indice-1a2b3c.js"></script></head>'
    '<body><div id="raiz"></div></body></html>'
)
GUION = "console.log('silice');"


def _cliente(ip: str = IP_LOCAL[0]) -> TestClient:
    return TestClient(app, base_url=ANFITRION, client=(ip, 50000), raise_server_exceptions=False)


def _cabeceras_de_seguridad(respuesta) -> None:
    assert respuesta.headers["content-security-policy"] == CSP
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert respuesta.headers["referrer-policy"] == "no-referrer"


@pytest.fixture
def dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Una interfaz «compilada» falsa, con un secreto al lado (fuera de `dist`)."""
    carpeta = tmp_path / "frontend-desktop" / "dist"
    (carpeta / "assets").mkdir(parents=True)
    (carpeta / "index.html").write_text(INDICE, encoding="utf-8")
    (carpeta / "assets" / "indice-1a2b3c.js").write_text(GUION, encoding="utf-8")
    (tmp_path / "frontend-desktop" / "secreto.txt").write_text("no se sirve", encoding="utf-8")
    monkeypatch.setattr(interfaz, "DIST", carpeta)
    return carpeta


def test_la_ruta_por_omision_es_la_del_repositorio() -> None:
    assert interfaz.DIST == config.RAIZ / "frontend-desktop" / "dist"


def test_app_sin_compilar_da_404_con_mensaje(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(interfaz, "DIST", tmp_path / "no-existe")
    for ruta in ("/app/", "/app/index.html", "/app/assets/indice.js"):
        respuesta = _cliente().get(ruta)
        assert respuesta.status_code == 404, ruta
        assert respuesta.json() == {"detalle": MENSAJE_SIN_COMPILAR}
        _cabeceras_de_seguridad(respuesta)


def test_app_sirve_index_con_csp(dist: Path) -> None:
    respuesta = _cliente().get("/app/")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert respuesta.text == INDICE
    _cabeceras_de_seguridad(respuesta)
    assert respuesta.headers["cache-control"] == "no-cache"
    directo = _cliente().get("/app/index.html")
    assert directo.status_code == 200 and directo.headers["cache-control"] == "no-cache"


def test_app_sirve_los_recursos_con_las_mismas_cabeceras(dist: Path) -> None:
    respuesta = _cliente().get("/app/assets/indice-1a2b3c.js")
    assert respuesta.status_code == 200 and respuesta.text == GUION
    _cabeceras_de_seguridad(respuesta)
    assert "no-cache" not in respuesta.headers.get("cache-control", "")


def test_app_redirige_a_la_barra_final(dist: Path) -> None:
    respuesta = _cliente().get("/app", follow_redirects=False)
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == "/app/"
    _cabeceras_de_seguridad(respuesta)


def test_un_archivo_que_no_existe_da_404_con_cabeceras(dist: Path) -> None:
    respuesta = _cliente().get("/app/no-existe.js")
    assert respuesta.status_code == 404 and "detalle" in respuesta.json()
    _cabeceras_de_seguridad(respuesta)


@pytest.mark.parametrize(
    "ruta", ["/app/%2e%2e/secreto.txt", "/app/..%2fsecreto.txt", "/app/%2e%2e%5csecreto.txt"]
)
def test_app_no_sale_de_su_carpeta(dist: Path, ruta: str) -> None:
    respuesta = _cliente().get(ruta)
    assert respuesta.status_code == 404
    assert "no se sirve" not in respuesta.text


def test_app_solo_admite_lectura(dist: Path) -> None:
    respuesta = _cliente().post("/app/", content=b"x")
    assert respuesta.status_code == 405
    _cabeceras_de_seguridad(respuesta)


def test_app_no_pide_clave_ni_esta_en_el_esquema(dist: Path) -> None:
    assert _cliente().get("/app/").status_code == 200
    assert not any(camino.startswith("/app") for camino in app.openapi()["paths"])


def test_app_pasa_por_la_proteccion_de_red(dist: Path) -> None:
    assert _cliente(ip="8.8.8.8").get("/app/").status_code == 403
    ajeno = TestClient(app, base_url="http://atacante.ejemplo", client=IP_LOCAL)
    assert ajeno.get("/app/").status_code == 400


def test_ninguna_clave_en_el_html_servido(dist: Path) -> None:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(destino, Destino.INSTALACION)
    clave = crear_clave_de_prueba()
    _, secreto = clave.split(".")
    respuesta = _cliente().get("/app/", headers={CABECERA: clave})
    assert respuesta.status_code == 200
    assert secreto not in respuesta.text and clave not in respuesta.text
    assert "set-cookie" not in respuesta.headers
    for archivo in dist.rglob("*"):
        if archivo.is_file():
            assert secreto not in archivo.read_text(encoding="utf-8")


def test_la_csp_no_permite_unsafe_eval_ni_anfitriones_externos() -> None:
    directivas = {
        partes[0]: partes[1:]
        for partes in (d.split() for d in interfaz.CABECERAS["Content-Security-Policy"].split(";"))
    }
    assert interfaz.CABECERAS["Content-Security-Policy"] == CSP
    fuentes = [f for valores in directivas.values() for f in valores]
    assert "'unsafe-eval'" not in fuentes and "'wasm-unsafe-eval'" not in fuentes
    assert not [f for f in fuentes if "://" in f or f in {"*", "http:", "https:", "ws:", "wss:"}]
    assert directivas["default-src"] == ["'self'"]
    assert directivas["script-src"] == ["'self'"]  # sin 'unsafe-inline' en guiones
    assert directivas["object-src"] == ["'none'"]
    assert directivas["frame-ancestors"] == ["'none'"]
    assert directivas["base-uri"] == ["'none'"]


def test_portada_en_raiz_sirve_html_autocontenido_con_csp_y_sin_urls_externas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`GET /` entrega la portada independiente de Sílice incluso sin `dist` compilado, con CSP,
    `Cache-Control: no-cache`, enlaces a `/app/`, cero scripts inline y cero URLs externas."""
    monkeypatch.setattr(interfaz, "DIST", tmp_path / "no-existe")
    respuesta = _cliente().get("/")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    _cabeceras_de_seguridad(respuesta)
    assert respuesta.headers["cache-control"] == "no-cache"

    html = respuesta.text
    assert "Presupuestos de obra verificables, celda por celda." in html
    assert "SISTEMA LOCAL DE ANÁLISIS DE PRECIOS UNITARIOS · ARITMÉTICA EXACTA" in html
    assert "Iniciar sesión en Sílice" in html
    assert 'href="/app/"' in html
    for fragmento in (
        "Cálculo exacto en Decimal (sin float)",
        "Bases SQLite locales por carpeta",
        "Cero telemetría externa",
        "HOJA: PLAN DE PAGOS · Inspección forense",
        "1.740,89 USD",
        "1.586,61 USD",
        "PRESUPUESTO!F12",
        "VALUACIONES!J48",
        "COVENIN!C104",
        "01 / Núcleo APU Multidominio",
        "02 / Auditoría Forense Excel L1–L7",
        "03 / Control de Obra y Valor Ganado IBCS",
        "04 / Moneda, Índices BCV y Riesgo ML",
        "05 / Producción de Cantera y Áridos",
        "06 / Gobernanza Local SHA-256 y Respaldos",
        "Administrador Master",
        "Rol Arma",
        "Rol Revisa",
    ):
        assert fragmento in html, fragmento

    assert "<script" not in html.lower()
    assert "http://" not in html and "https://" not in html

    cabecera = _cliente().head("/")
    assert cabecera.status_code == 200
    _cabeceras_de_seguridad(cabecera)
    assert "/" not in app.openapi()["paths"]
    assert _cliente(ip="8.8.8.8").get("/").status_code == 403


def test_portada_destaca_descarga_escritorio_y_acceso_web_de_prueba(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`GET /` presenta el botón principal «Descargar el sistema Sílice» para el ambiente de
    escritorio propio y distingue el inicio de sesión en `/app/` como ambiente web de prueba."""
    monkeypatch.setattr(interfaz, "DIST", tmp_path / "no-existe")
    html = _cliente().get("/").text
    assert "Descargar el sistema Sílice" in html
    assert 'href="#descargar"' in html
    assert "ambiente de prueba web" in html.lower()
    assert "ambiente de escritorio propio" in html.lower()
