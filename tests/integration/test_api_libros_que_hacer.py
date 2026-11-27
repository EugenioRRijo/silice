"""`GET /v1/libros/que-hacer`: el catálogo del «Qué hacer» de un libro (B2, ficha-b2 §3.3).

Solo lectura y sin recibir el libro: devuelve lo que `aplicacion/que_hacer.py` escribe. Mismo
acceso que las demás rutas de libros (clave de API o sesión con `leer_proyecto`). No cambia
`POST /v1/libros/auditoria`: el front junta las dos respuestas por código.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.proteccion import MENSAJE_SIN_CLAVE
from api.sesion_web import MENSAJE_SIN_SESION
from aplicacion import que_hacer as qh
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL

RUTA = "/v1/libros/que-hacer"


def test_con_clave_valida_responde_el_catalogo_completo(cliente) -> None:
    r = cliente.get(RUTA)
    assert r.status_code == 200, r.text
    assert r.json() == qh.catalogo()


def test_cada_regla_del_libro_trae_su_guia_con_su_codigo(cliente) -> None:
    cuerpo = cliente.get(RUTA).json()
    for codigo in ("L1", "L4", "L5", "F1", "R2"):
        guia = cuerpo["reglas"][codigo]
        assert guia["codigo"] == codigo
        assert guia["generico"] is False
        assert guia["que_hacer"]
    assert cuerpo["alertas"]["USD-Bs"]["codigo"] == "alerta:usd-bs"
    assert cuerpo["generico"]["generico"] is True


def test_sin_clave_valida_401_con_el_mensaje_de_cada_caso() -> None:
    for clave, mensaje in (
        (None, MENSAJE_SIN_SESION),
        ("", MENSAJE_SIN_CLAVE),
        ("desconocida.secreto", MENSAJE_SIN_CLAVE),
    ):
        cabeceras = {} if clave is None else {CABECERA: clave}
        ajeno = TestClient(app, base_url=ANFITRION, client=IP_LOCAL, headers=cabeceras)
        r = ajeno.get(RUTA)
        assert r.status_code == 401, (clave, r.text)
        assert r.json() == {"detalle": mensaje}


def test_no_guarda_ni_cambia_nada_y_se_puede_pedir_dos_veces(cliente) -> None:
    primera = cliente.get(RUTA).json()
    segunda = cliente.get(RUTA).json()
    assert primera == segunda


def test_la_ruta_no_se_cuela_en_la_auditoria_sellada() -> None:
    """`api/rutas/libros.py` no la declara: vive en su propio archivo."""
    from pathlib import Path

    fuente = (Path(__file__).resolve().parents[2] / "api" / "rutas" / "libros.py").read_text(
        encoding="utf-8"
    )
    assert "que-hacer" not in fuente
    assert "que_hacer" not in fuente
