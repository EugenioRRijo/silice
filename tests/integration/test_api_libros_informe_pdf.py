"""`POST /v1/libros/auditoria/pdf`: el informe de hallazgos de un libro en PDF (decisión P2 de
Eugenio, 2026-11-19; UC-25).

La ruta recibe lo mismo que `/v1/libros/auditoria` (el libro y la fecha de devolución), vuelve a
auditar con la misma fecha (misma fecha, mismo resultado) y responde el PDF del informe. No guarda
nada: ni el libro ni el PDF (RNF-28), y tampoco una fila nueva en el historial, porque la
auditoría que la persona ve en pantalla ya dejó la suya.

Oráculos, ninguno sale del código bajo prueba: la memoria de cálculo a mano de
`tests/fixtures/libros_empresa.py` (libro limpio: total general 5 055,52157, que se lee
«5.055,52»; con H1: el libro declara 4 876,56257, «4.876,56») y los hallazgos de H1 de
`test_api_libros.py` (F1, L4, L9 x2 de error; R2 y R7 informativos). El texto del PDF lo extrae
pdfplumber, otra biblioteca.
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import pdfplumber
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.proteccion import MENSAJE_SIN_CLAVE
from api.sesion_web import MENSAJE_SIN_SESION
from operacion import config
from operacion.base_datos import Destino, preparar_base
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL
from tests.fixtures.libros_empresa import APUS_LIMPIOS, con, construir_libro, libro_limpio

RUTA = "/v1/libros/auditoria/pdf"
FECHA_DEVOLUCION = "2026-10-13"
TIPO_PDF = "application/pdf"


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    plantilla = tmp_path_factory.mktemp("plantilla_libros_informe") / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path) -> None:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)


@pytest.fixture(scope="module")
def limpio():
    return libro_limpio()


@pytest.fixture(scope="module")
def con_h1():
    apus = (APUS_LIMPIOS[0], con(APUS_LIMPIOS[1], cd_sin_equipos=True), APUS_LIMPIOS[2])
    return construir_libro(apus)


def _pedir(cliente, datos: bytes, nombre: str = "libro.xlsx", **campos):
    formulario = {"fecha_devolucion": FECHA_DEVOLUCION, **campos}
    formulario = {k: v for k, v in formulario.items() if v is not None}
    return cliente.post(RUTA, files={"libro": (nombre, datos)}, data=formulario)


def _texto(contenido: bytes) -> str:
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)


def test_un_libro_limpio_baja_un_pdf_que_dice_que_cumple(cliente, limpio) -> None:
    r = _pedir(cliente, limpio.datos, nombre="obra ficticia.xlsx")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == TIPO_PDF
    assert r.headers["content-disposition"] == 'attachment; filename="hallazgos_obra_ficticia.pdf"'
    assert r.headers["cache-control"] == "no-store"
    assert r.content.startswith(b"%PDF")
    texto = _texto(r.content)
    for esperado in (
        "Hallazgos de la auditoría",
        "obra ficticia.xlsx",
        "31/07/2026",  # la PORTADA «Julio 2026»: fin de mes
        "13/10/2026",  # la fecha de devolución, escrita como la interfaz
        "Cumple",
        "Total general",
        "5.055,52",
    ):
        assert esperado in texto, esperado
    assert "No cumple" not in texto


def test_un_libro_con_h1_lista_sus_hallazgos_y_los_totales_de_cada_lado(cliente, con_h1) -> None:
    r = _pedir(cliente, con_h1.datos)
    assert r.status_code == 200, r.text
    texto = _texto(r.content)
    assert "No cumple" in texto
    assert "4 errores" in texto and "2 avisos informativos" in texto
    for esperado in ("F1", "L4", "L9", "R2", "R7", "4.876,56", "5.055,52", "154,28", "127,50"):
        assert esperado in texto, esperado
    assert "APU-02!G" in texto  # la celda de L4, tal como la muestra la lista


def test_el_pdf_no_deja_ninguna_fila_en_el_historial(cliente, limpio) -> None:
    assert _pedir(cliente, limpio.datos).status_code == 200
    assert cliente.get("/v1/auditorias-libro").json() == []


def test_con_la_misma_fecha_el_mismo_libro_da_el_mismo_texto(cliente, con_h1) -> None:
    primero = _texto(_pedir(cliente, con_h1.datos).content)
    segundo = _texto(_pedir(cliente, con_h1.datos).content)
    assert primero == segundo


@pytest.mark.parametrize("clave", [None, "", "desconocida.secreto"])
def test_sin_clave_valida_401_y_no_se_procesa_nada(limpio, monkeypatch, clave) -> None:
    import api.rutas.libros as libros

    llamadas: list[str] = []
    monkeypatch.setattr(libros, "procesar_libro", lambda *a, **k: llamadas.append("libro"))
    cabeceras = {} if clave is None else {CABECERA: clave}
    ajeno = TestClient(app, base_url=ANFITRION, client=IP_LOCAL, headers=cabeceras)
    r = _pedir(ajeno, limpio.datos)
    assert r.status_code == 401
    assert r.json() == {"detalle": MENSAJE_SIN_SESION if clave is None else MENSAJE_SIN_CLAVE}
    assert llamadas == []


def test_falta_la_fecha_o_el_archivo_no_es_xlsx(cliente, limpio) -> None:
    assert _pedir(cliente, limpio.datos, fecha_devolucion=None).status_code == 422
    r = _pedir(cliente, limpio.datos, nombre="libro.pdf")
    assert r.status_code == 415
    assert "xlsx" in r.json()["detalle"]


def test_un_fallo_inesperado_es_500_con_un_mensaje_fijo_y_sin_traza(
    cliente, limpio, monkeypatch
) -> None:
    import api.rutas.libros_informe as ruta

    def _roto(*args, **kwargs):
        raise RuntimeError("secreto-interno C:\\ruta\\privada")

    monkeypatch.setattr(ruta, "pdf_de_hallazgos", _roto)
    r = _pedir(cliente, limpio.datos)
    assert r.status_code == 500
    assert r.json() == {"detalle": "No se pudo preparar el PDF de hallazgos."}
    assert "secreto-interno" not in r.text
