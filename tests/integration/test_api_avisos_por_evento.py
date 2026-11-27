"""C11b por la API: preferencias de notificaciones y los avisos que nacen de un evento.

Contrato (oráculos escritos a mano):
- `GET /v1/notificaciones/preferencias` -> 200 `{categorias: [{categoria, titulo, descripcion,
  activa, aplica, obligatoria}]}`, las cuatro en su orden, de la cuenta de la sesión.
- `PUT /v1/notificaciones/preferencias` `{categorias: [{categoria, activa}]}` -> 200 con la misma
  forma. 422 con el motivo ante una categoría desconocida o repetida, o si quien revisa apaga
  `por_dictaminar`. Solo las propias: no hay forma de nombrar otra cuenta.
- 401 sin sesión; 403 con la clave de API (no es una persona) o sin CSRF / con `Origin` ajeno en el
  PUT; `Cache-Control: no-store`.
- Ganchos: Ana envía una versión -> Rita (revisa) la ve en `GET /v1/notificaciones`; Rita la
  devuelve -> Ana ve «fue devuelta»; a los 2 días hábiles sin dictamen, Rita ve el recordatorio al
  listar; el administrador carga la referencia MaPreX -> Ana (arma) la ve, Rita y él no.

Carpetas: `silice.db` (la de la empresa) y `vivienda.db` con la «Vivienda Demo 80 m2» (VIV-001)
guardada por «Ana <ana>» (`tests/fixtures/carpeta_aprobaciones.py`). Datos ficticios.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from api.rutas import aprobaciones as rutas_aprobaciones
from api.rutas import notificaciones as rutas_notificaciones
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import OBRA, sembrar_vivienda
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    ORIGEN,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

RUTA = "/v1/notificaciones/preferencias"
VIERNES = datetime(2026, 11, 20, 10, 0)
MARTES = datetime(2026, 11, 24, 9, 0)
AJENO = "http://otro.sitio.example"
DESCRIPCIONES = {
    "por_dictaminar": (
        "Versiones por dictaminar",
        "Una versión espera su dictamen, y un recordatorio si lleva 2 días hábiles esperando.",
    ),
    "dictamen": (
        "Dictamen de sus versiones",
        "Una versión que usted envió fue aprobada, devuelta o retirada.",
    ),
    "compras": (
        "Compras por pedir",
        "Un material de una obra en la que trabajó debe pedirse pronto o ya debía pedirse.",
    ),
    "listas_de_precios": (
        "Listas de precios nuevas",
        "Se cargó una lista o una referencia de precios nueva.",
    ),
    "entregas": (
        "Entregas al cliente",
        "Se acerca o ya llegó la fecha de entrega al cliente de una obra en la que trabajó.",
    ),
}


def _categorias(**cambios: tuple[bool, bool, bool]) -> list[dict]:
    """Las cinco categorías con (activa, aplica, obligatoria) de cada una."""
    return [
        {
            "categoria": categoria,
            "titulo": titulo,
            "descripcion": descripcion,
            "activa": cambios[categoria][0],
            "aplica": cambios[categoria][1],
            "obligatoria": cambios[categoria][2],
        }
        for categoria, (titulo, descripcion) in DESCRIPCIONES.items()
    ]


DE_ANA = _categorias(
    por_dictaminar=(True, False, False),
    dictamen=(True, True, False),
    compras=(True, True, False),
    listas_de_precios=(True, True, False),
    entregas=(True, True, False),
)
DE_RITA = _categorias(
    por_dictaminar=(True, True, True),
    dictamen=(True, False, False),
    compras=(True, False, False),
    listas_de_precios=(True, False, False),
    entregas=(True, False, False),
)


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("avisos_por_evento_api")
    vivienda, empresa = carpeta / "vivienda.db", carpeta / "silice.db"
    preparar_base(empresa)
    preparar_base(vivienda)
    motor = crear_motor(f"sqlite:///{vivienda.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            sembrar_vivienda(s)
    finally:
        motor.dispose()
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "vivienda.db": vivienda,
        "silice.db": empresa,
    }


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos_dir = config.carpeta_casos()
    casos_dir.mkdir(parents=True, exist_ok=True)
    for nombre in ("vivienda.db", "silice.db"):
        (casos_dir / nombre).write_bytes(_plantillas[nombre].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    _reloj(monkeypatch, VIERNES)
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _reloj(monkeypatch: pytest.MonkeyPatch, cuando: datetime) -> None:
    monkeypatch.setattr(rutas_aprobaciones, "ahora", lambda: cuando)
    monkeypatch.setattr(rutas_notificaciones, "ahora", lambda: cuando)


def _en_vivienda(login: str):
    navegador, ficha = con_cuenta(app, login)
    elegida = navegador.post(
        "/v1/casos/actual", json={"nombre": "vivienda.db"}, headers=protegida(ficha)
    )
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


def _titulos(navegador) -> list[str]:
    respuesta = navegador.get("/v1/notificaciones")
    assert respuesta.status_code == 200, respuesta.text
    return [n["titulo"] for n in respuesta.json()["notificaciones"]]


# --- preferencias ---------------------------------------------------------------------------------


def test_sin_sesion_401_y_con_la_clave_403() -> None:
    sin = cliente(app)
    assert sin.get(RUTA).status_code == 401
    assert sin.put(RUTA, json={"categorias": []}, headers={"Origin": ORIGEN}).status_code == 401
    secreto = crear_clave_de_prueba()
    con_clave = cliente(app).get(RUTA, headers={CABECERA: secreto})
    assert con_clave.status_code == 403
    assert con_clave.headers["cache-control"] == "no-store"


def test_cada_cuenta_ve_las_suyas_segun_su_rol() -> None:
    ana, _ = con_cuenta(app, "ana")
    respuesta = ana.get(RUTA)
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {"categorias": DE_ANA}
    rita, _ = con_cuenta(app, "rita")
    assert rita.get(RUTA).json() == {"categorias": DE_RITA}


def test_apagar_compras_cambia_solo_las_de_quien_lo_pide() -> None:
    ana, ficha = con_cuenta(app, "ana")
    respuesta = ana.put(
        RUTA,
        json={"categorias": [{"categoria": "compras", "activa": False}]},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 200, respuesta.text
    esperada = [
        {**c, "activa": False} if c["categoria"] == "compras" else c for c in DE_ANA
    ]
    assert respuesta.json() == {"categorias": esperada}
    assert ana.get(RUTA).json() == {"categorias": esperada}
    rita, _ = con_cuenta(app, "rita")
    assert rita.get(RUTA).json() == {"categorias": DE_RITA}


@pytest.mark.parametrize(
    ("login", "cuerpo", "detalle"),
    [
        (
            "rita",
            {"categorias": [{"categoria": "por_dictaminar", "activa": False}]},
            "Quien revisa recibe siempre las versiones que esperan su dictamen: esa categoría "
            "no se puede apagar.",
        ),
        (
            "ana",
            {"categorias": [{"categoria": "inexistente", "activa": False}]},
            "No existe la categoría «inexistente».",
        ),
        (
            "ana",
            {
                "categorias": [
                    {"categoria": "compras", "activa": False},
                    {"categoria": "compras", "activa": True},
                ]
            },
            "La categoría «compras» está repetida.",
        ),
    ],
)
def test_lo_que_no_se_puede_guardar_es_422_sin_cambiar_nada(
    login: str, cuerpo: dict, detalle: str
) -> None:
    navegador, ficha = con_cuenta(app, login)
    antes = navegador.get(RUTA).json()
    respuesta = navegador.put(RUTA, json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"] == detalle
    assert navegador.get(RUTA).json() == antes


def test_el_put_exige_csrf_y_origin_propio() -> None:
    ana, ficha = con_cuenta(app, "ana")
    cuerpo = {"categorias": [{"categoria": "compras", "activa": False}]}
    assert ana.put(RUTA, json=cuerpo, headers={"Origin": ORIGEN}).status_code == 403
    assert ana.put(RUTA, json=cuerpo, headers=protegida(ficha, origen=AJENO)).status_code == 403
    assert ana.get(RUTA).json() == {"categorias": DE_ANA}


# --- los ganchos ----------------------------------------------------------------------------------


def test_un_envio_avisa_a_quien_revisa_y_el_dictamen_a_quien_envio(monkeypatch) -> None:
    ana, ficha_ana = _en_vivienda("ana")
    rita, ficha_rita = con_cuenta(app, "rita")
    enviado = ana.post(
        "/v1/aprobaciones",
        json={"proyecto": OBRA, "version": "VIV-001", "nota": "Primera entrega"},
        headers=protegida(ficha_ana),
    )
    assert enviado.status_code == 201, enviado.text
    envio_id = enviado.json()["id"]
    [aviso] = rita.get("/v1/notificaciones").json()["notificaciones"]
    assert (aviso["gravedad"], aviso["titulo"], aviso["detalle"], aviso["enlace"]) == (
        "info",
        "VIV-001 de «Vivienda Demo 80 m2» espera su dictamen",
        "La envió Ana el 20/11/2026. Nota: Primera entrega",
        {"texto": "Ver la aprobación", "ruta": "/obra/vivienda.db/1/aprobaciones"},
    )
    assert _titulos(ana) == []

    abierto = rita.post(
        "/v1/aprobaciones/abrir",
        json={"caso": "vivienda.db", "envio_id": envio_id},
        headers=protegida(ficha_rita),
    )
    assert abierto.status_code == 200, abierto.text
    _reloj(monkeypatch, MARTES)
    devuelto = rita.post(
        f"/v1/aprobaciones/{envio_id}/dictamen",
        json={"resultado": "devuelta", "notas": "Falta el acero de la losa."},
        headers=protegida(ficha_rita),
    )
    assert devuelto.status_code == 201, devuelto.text
    [cierre] = ana.get("/v1/notificaciones").json()["notificaciones"]
    assert (cierre["gravedad"], cierre["titulo"], cierre["detalle"]) == (
        "advertencia",
        "Su versión VIV-001 de «Vivienda Demo 80 m2» fue devuelta",
        "Rita la devolvió el 24/11/2026. Notas: Falta el acero de la losa.",
    )
    # Ya tiene dictamen: al listar el martes, Rita no recibe recordatorio.
    assert _titulos(rita) == ["VIV-001 de «Vivienda Demo 80 m2» espera su dictamen"]


def test_al_listar_quien_revisa_recibe_el_recordatorio_a_los_2_dias_habiles(monkeypatch) -> None:
    ana, ficha_ana = _en_vivienda("ana")
    rita, _ = con_cuenta(app, "rita")
    enviado = ana.post(
        "/v1/aprobaciones",
        json={"proyecto": OBRA, "version": "VIV-001", "nota": ""},
        headers=protegida(ficha_ana),
    )
    assert enviado.status_code == 201, enviado.text
    _reloj(monkeypatch, datetime(2026, 11, 23, 9, 0))  # lunes: 1 día hábil
    assert _titulos(rita) == ["VIV-001 de «Vivienda Demo 80 m2» espera su dictamen"]
    _reloj(monkeypatch, MARTES)  # 2 días hábiles
    assert _titulos(rita) == [
        "VIV-001 de «Vivienda Demo 80 m2» sigue esperando su dictamen",
        "VIV-001 de «Vivienda Demo 80 m2» espera su dictamen",
    ]
    assert len(_titulos(rita)) == 2  # no se repite


def test_la_referencia_cargada_avisa_a_quienes_arman(monkeypatch) -> None:
    admin, ficha = con_cuenta(app, "admin")
    cargada = admin.post("/v1/precios-empresa/referencia", headers=protegida(ficha))
    assert cargada.status_code == 200, cargada.text
    titulo = "Lista de precios nueva: «MaPreX julio 2026 en Bs»"
    ana, _ = con_cuenta(app, "ana")
    [aviso] = ana.get("/v1/notificaciones").json()["notificaciones"]
    assert (aviso["titulo"], aviso["detalle"], aviso["enlace"]) == (
        titulo,
        "Admin de Prueba la cargó en la carpeta de la empresa.",
        {"texto": "Ver los precios de la empresa", "ruta": "/precios/listas"},
    )
    rita, _ = con_cuenta(app, "rita")
    assert _titulos(rita) == [] and _titulos(admin) == []
    # Cargarla otra vez no escribe nada ni avisa de nuevo.
    otra_vez = admin.post("/v1/precios-empresa/referencia", headers=protegida(ficha))
    assert otra_vez.status_code == 200
    assert _titulos(ana) == [titulo]
