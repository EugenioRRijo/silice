"""`/v1/libros`: auditar, devolver calcado y revisar el PDF simple por la API (RF-109, UC-25; spec
1.5 §5; RF-102 a RF-108 vistos desde la frontera HTTP; RNF-21 en el tope del cuerpo y de páginas).

Las tres rutas de `api/rutas/libros.py` se ejercen con el cliente HTTP de las pruebas de
integración (`tests/integration/conftest.py`: sesión en memoria con la línea base y una clave de
API real en la `instalacion.db` temporal), el mismo patrón que `test_api_auditorias.py`.

Oráculos, ninguno sale de la función bajo prueba:

- Totales del libro limpio: la memoria de cálculo a mano de `tests/fixtures/libros_empresa.py`
  (`MEMORIA`: SUBSINIVA 4 358,20825; IVATOT 697,31332; TOTALGEN 5 055,52157; P.U. 14,486725,
  30,2121875 y 4,056525).
- H1 (`cd_sin_equipos` en APU-02): el CD guardado omite EQ = 1,59375, así que el P guardado baja
  1,59375 × 1,1 (ADMON) × 1,1 (UTIL) = 1,9284375 y el total sin IVA 1,9284375 × 80 = 154,275,
  que se informa en céntimos ROUND_HALF_UP: 154.28. El desglose sin equipos se aparta en
  1,59375 × 80 = 127,50. Totales del libro con H1: 4 358,20825 − 154,275 = 4 203,93325;
  IVA 0,16 × 4 203,93325 = 672,62932; total 4 876,56257.
- USD-Bs: tasas sembradas en la base de la prueba (100 Bs/USD al 31/07/2026, fin del mes de
  «Julio 2026» de la PORTADA; 110 al 13/10/2026, la fecha de devolución): cada precio en Bs sube
  (110 − 100) ÷ 100 = 10 %. MT-01 a 10 USD: 1 000 Bs -> 1 100 Bs. La frontera del umbral es
  0,10 (pasa: |variación| ≥ umbral) contra 0,1000001 (dentro).
- PDF simple: 5 × 289,00 = 1 445,00 y el PDF imprime 1 446,65: L10 «aritmética de fila» con
  impacto 1 446,65 − 1 445,00 = 1,65; la suma de renglones (1 446,65) sí da el TOTAL PRESUPUESTO.
- Los mensajes de error de la guardia y del lector son los literales que el spec manda mostrar
  tal cual (F-D10).

Nada se escribe en disco ni en la base (F-D9): se cuentan las filas de todas las tablas antes y
después, y se vigila toda apertura de archivo para escribir durante las peticiones.
"""

from __future__ import annotations

import builtins
import io
import os
import re
import shutil
import tempfile
from collections import Counter
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from sqlalchemy import func, select

from api.main import app
from api.proteccion import LIMITE_CUERPO, MENSAJE_SIN_CLAVE
from api.sesion_web import MENSAJE_SIN_SESION
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from core.models.base import Base
from operacion import config
from operacion.base_datos import Destino, preparar_base
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    FILA_PRIMERA_PARTIDA,
    INSUMOS,
    MEMORIA,
    Siembra,
    con,
    construir_libro,
    libro_limpio,
)

FECHA_DEVOLUCION = "2026-10-13"
TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TOL_CELDA = Decimal("0.005")  # ficha de pruebas: ±0,005 por celda de Excel
RUTAS_DEL_LIBRO = ("/v1/libros/auditoria", "/v1/libros/devolucion")


# --- Ayudas ---


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    """Una `instalacion.db` ya migrada, una vez por módulo (mismo patrón que
    `test_api_clave.py`): cada prueba parte de una copia y no paga las migraciones."""
    plantilla = tmp_path_factory.mktemp("plantilla_libros") / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path) -> None:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)


@pytest.fixture(scope="module")
def limpio():
    """El libro limpio, contrastado contra `MEMORIA` al construirse (una vez por módulo)."""
    return libro_limpio()


@pytest.fixture(scope="module")
def con_h1():
    """APU-02 con el CD sin equipos (H1)."""
    apus = (APUS_LIMPIOS[0], con(APUS_LIMPIOS[1], cd_sin_equipos=True), APUS_LIMPIOS[2])
    return construir_libro(apus)


def _post(cliente, ruta: str, datos: bytes, nombre: str = "libro.xlsx", archivos=None, **campos):
    formulario = {"fecha_devolucion": FECHA_DEVOLUCION, **campos}
    formulario = {k: v for k, v in formulario.items() if v is not None}
    return cliente.post(ruta, files={"libro": (nombre, datos), **(archivos or {})}, data=formulario)


def _auditar(cliente, datos: bytes, **campos):
    return _post(cliente, "/v1/libros/auditoria", datos, **campos)


def _hallazgos(cuerpo: dict) -> Counter:
    return Counter(
        (h["codigo"], h["severidad"], h["impacto"], h["accion"]) for h in cuerpo["hallazgos"]
    )


def _pdf_simple(renglones, total: str, *, paginas_de_relleno: int = 0) -> bytes:
    """PDF simple mínimo: página «Presupuesto» con la cabecera Items, Descripción, Unidad,
    Cantidad, Precio Unitario y Total, los renglones dados y «TOTAL PRESUPUESTO <total>».
    `paginas_de_relleno` añade páginas sin tabla (para el tope de páginas, RNF-21)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Helvetica", 9)
    c.drawString(40, 790, "Presupuesto")
    c.drawString(40, 770, "001 Fecha: 18/05/2026")
    for x, texto in ((40, "Items"), (80, "Descripción"), (260, "Unidad"), (320, "Cantidad")):
        c.drawString(x, 720, texto)
    c.drawString(390, 720, "Precio Unitario")
    c.drawString(500, 720, "Total")
    y = 700
    for item, descripcion, unidad, cantidad, precio, monto in renglones:
        for x, texto in (
            (40, item),
            (80, descripcion),
            (260, unidad),
            (320, cantidad),
            (390, precio),
            (500, monto),
        ):
            c.drawString(x, y, texto)
        y -= 18
    c.drawString(80, y - 6, "TOTAL PRESUPUESTO")
    c.drawString(500, y - 6, total)
    c.showPage()
    for _ in range(paginas_de_relleno):
        c.setFont("Helvetica", 9)
        c.drawString(40, 790, "Anexo sin tablas")
        c.showPage()
    c.save()
    return buf.getvalue()


RENGLON_MAL = ("1", "Friso liso (ficticio)", "m2", "5", "289,00", "1446,65")


def _pdf_sin_tablas() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(40, 790, "Carta de presentación sin tablas (ficticia)")
    c.showPage()
    c.save()
    return buf.getvalue()


def _sembrar_tasas(sesion) -> None:
    """Tasas del BCV de prueba (ficticias) en la base de la sesión: 100 y 110 Bs/USD."""
    registrar_importacion(
        sesion,
        definicion_tasa("venta"),
        [
            Observacion(date(2026, 7, 31), Decimal("100")),
            Observacion(date(2026, 10, 13), Decimal("110")),
        ],
        archivo="tasas_de_prueba.xls",
        huella="a" * 64,
        fuente="Tasas ficticias de la prueba",
        fecha_descarga=date(2026, 10, 13),
        responsable="pruebas",
        filas_leidas=2,
        filas_rechazadas=0,
    )


def _filas_por_tabla(sesion) -> dict[str, int]:
    return {
        t.name: sesion.execute(select(func.count()).select_from(t)).scalar_one()
        for t in Base.metadata.sorted_tables
    }


_MODOS_DE_ESCRITURA = ("w", "a", "x", "+")
_BANDERAS_DE_ESCRITURA = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


@pytest.fixture
def escrituras(monkeypatch):
    """Lista de los archivos que alguien abre para escribir mientras corre la prueba. Solo observa:
    delega siempre en la función original (no cambia el comportamiento de la ruta)."""
    vistos: list[str] = []
    abrir, abrir_io, abrir_os = builtins.open, io.open, os.open

    def _open(archivo, modo="r", *args, **kwargs):
        if isinstance(modo, str) and any(m in modo for m in _MODOS_DE_ESCRITURA):
            vistos.append(f"open({archivo!r}, {modo!r})")
        return abrir(archivo, modo, *args, **kwargs)

    def _open_io(archivo, modo="r", *args, **kwargs):
        if isinstance(modo, str) and any(m in modo for m in _MODOS_DE_ESCRITURA):
            vistos.append(f"io.open({archivo!r}, {modo!r})")
        return abrir_io(archivo, modo, *args, **kwargs)

    def _open_os(ruta, banderas, *args, **kwargs):
        if banderas & _BANDERAS_DE_ESCRITURA:
            vistos.append(f"os.open({ruta!r})")
        return abrir_os(ruta, banderas, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open)
    monkeypatch.setattr(io, "open", _open_io)
    monkeypatch.setattr(os, "open", _open_os)
    for nombre in ("mkstemp", "mkdtemp", "TemporaryFile", "NamedTemporaryFile"):
        original = getattr(tempfile, nombre)

        def _vigilado(*args, _n=nombre, _o=original, **kwargs):
            vistos.append(f"tempfile.{_n}")
            return _o(*args, **kwargs)

        monkeypatch.setattr(tempfile, nombre, _vigilado)
    return vistos


# --- Clave de API (RF-98, RF-109) ---


@pytest.mark.parametrize(
    "ruta",
    ["/v1/libros/auditoria", "/v1/libros/devolucion", "/v1/libros/pdf", "/v1/libros/replica"],
)
def test_sin_clave_valida_401_y_no_se_procesa_nada(cliente, limpio, monkeypatch, ruta):
    """Clave vacía o desconocida: 401 con el mensaje de la clave; sin la cabecera (ni cookie),
    401 con el de la sesión (RS2-5: sin `X-Silice-Clave` se busca la cookie del navegador). En
    ningún caso la ruta llega a leer ni a procesar nada (el acceso se exige antes)."""
    import api.rutas.libros as rutas

    llamadas: list[str] = []
    monkeypatch.setattr(rutas, "procesar_libro", lambda *a, **k: llamadas.append("libro"))
    monkeypatch.setattr(rutas, "auditar_pdf_simple", lambda *a, **k: llamadas.append("pdf"))
    monkeypatch.setattr(rutas, "replicar_libro", lambda *a, **k: llamadas.append("replica"))
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    for clave, mensaje in (
        (None, MENSAJE_SIN_SESION),
        ("", MENSAJE_SIN_CLAVE),
        ("desconocida.secreto", MENSAJE_SIN_CLAVE),
    ):
        cabeceras = {} if clave is None else {CABECERA: clave}
        ajeno = TestClient(app, base_url=ANFITRION, client=IP_LOCAL, headers=cabeceras)
        if ruta.endswith("/pdf"):
            r = ajeno.post(ruta, files={"pdf": ("p.pdf", pdf)})
        else:
            r = _post(ajeno, ruta, limpio.datos)
        assert r.status_code == 401, (clave, r.text)
        assert r.json() == {"detalle": mensaje}
    assert llamadas == []


def test_con_clave_valida_las_cuatro_rutas_responden_200(cliente, limpio) -> None:
    assert _post(cliente, "/v1/libros/auditoria", limpio.datos).status_code == 200
    assert _post(cliente, "/v1/libros/devolucion", limpio.datos).status_code == 200
    replica = cliente.post("/v1/libros/replica", files={"libro": ("libro.xlsx", limpio.datos)})
    assert replica.status_code == 200
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    assert cliente.post("/v1/libros/pdf", files={"pdf": ("p.pdf", pdf)}).status_code == 200


# --- POST /v1/libros/auditoria: libro limpio ---


def test_libro_limpio_totales_como_texto_iguales_a_la_memoria(cliente, limpio) -> None:
    r = _auditar(cliente, limpio.datos)
    assert r.status_code == 200, r.text
    d = r.json()
    # Totales leídos del libro: el texto exacto de la memoria a mano.
    assert d["totales_libro"] == {
        "SUBSINIVA": "4358.20825",
        "IVATOT": "697.31332",
        "TOTALGEN": "5055.52157",
    }
    # Totales de Silice: texto (nunca número JSON) y el mismo valor exacto que la memoria.
    assert set(d["totales_silice"]) == {"SUBSINIVA", "IVATOT", "TOTALGEN"}
    for clave, esperado in (
        ("SUBSINIVA", Decimal("4358.20825")),
        ("IVATOT", Decimal("697.31332")),
        ("TOTALGEN", Decimal("5055.52157")),
    ):
        texto = d["totales_silice"][clave]
        assert isinstance(texto, str)
        assert Decimal(texto) == esperado == MEMORIA[clave]
    assert d["libro"]["nombre"] == "libro.xlsx"
    assert len(d["libro"]["sha256"]) == 64
    # Sin fecha_libro, la de la PORTADA «Julio 2026»: el último día del mes (F-D8).
    assert d["fecha_libro"] == "2026-07-31"
    assert d["fecha_devolucion"] == FECHA_DEVOLUCION
    assert d["metadatos"]["fecha"] == FECHA_DEVOLUCION
    assert d["metadatos"]["fecha_libro"] == "2026-07-31"
    assert d["metadatos"]["sha256_origen"] == d["libro"]["sha256"]


def test_libro_limpio_da_exactamente_r2_y_r7_informativos(cliente, limpio) -> None:
    d = _auditar(cliente, limpio.datos).json()
    assert _hallazgos(d) == Counter(
        {("R2", "INFO", None, "informado"): 1, ("R7", "INFO", None, "informado"): 1}
    )
    assert d["cumple"] is True
    assert d["por_severidad"] == {"INFO": 2}


def test_libro_limpio_alertas_sin_fuente_y_usd_bs_no_contrastable(cliente, sesion, limpio) -> None:
    from core import models

    # Precondición del oráculo: la base de la prueba no tiene tasas ni lista de empresa.
    assert sesion.query(models.ValorIndice).count() == 0
    assert sesion.query(models.ListaEmpresa).count() == 0
    d = _auditar(cliente, limpio.datos).json()
    por_tipo = Counter(a["tipo"] for a in d["alertas"])
    assert por_tipo == {"sin fuente": 2, "USD-Bs": len(INSUMOS)}
    sin_fuente = {a["codigo"]: a for a in d["alertas"] if a["tipo"] == "sin fuente"}
    assert set(sin_fuente) == {"MT-03", "EQ-01"}
    assert sin_fuente["MT-03"]["fuente"] == "REFERENCIAL — ajustar"
    assert "«REFERENCIAL — ajustar»" in sin_fuente["MT-03"]["mensaje"]
    assert sin_fuente["EQ-01"]["fuente"] == ""
    assert "está vacía" in sin_fuente["EQ-01"]["mensaje"]
    bs = [a for a in d["alertas"] if a["tipo"] == "USD-Bs"]
    assert {a["codigo"] for a in bs} == {i.codigo for i in INSUMOS}
    for a in bs:
        assert a["tasa"] is None and a["precio_bs"] is None and a["variacion"] is None
        assert a["mensaje"] == (
            "no contrastable: la instalación no tiene la tasa del BCV de 2026-07-31 ni la de "
            "2026-10-13"
        )
    # El precio viaja como texto, igual al de INSUMOS.
    precios = {i.codigo: i.precio for i in INSUMOS}
    for a in d["alertas"]:
        assert isinstance(a["precio"], str) and Decimal(a["precio"]) == precios[a["codigo"]]
        assert a["moneda"] == "USD"


def test_con_tasas_en_la_base_usd_bs_calculado_a_mano(cliente, sesion, limpio) -> None:
    _sembrar_tasas(sesion)
    d = _auditar(cliente, limpio.datos).json()
    bs = {a["codigo"]: a for a in d["alertas"] if a["tipo"] == "USD-Bs"}
    assert set(bs) == {i.codigo for i in INSUMOS}
    mt01 = bs["MT-01"]
    assert Decimal(mt01["tasa"]) == Decimal("110")
    assert Decimal(mt01["precio_bs"]) == Decimal("1100")  # 10 USD × 110
    assert Decimal(mt01["variacion"]) == Decimal("0.1")  # (1100 − 1000) ÷ 1000
    assert "1000 Bs al 2026-07-31 (tasa 100)" in mt01["mensaje"]
    assert "1100 Bs al 2026-10-13 (tasa 110)" in mt01["mensaje"]
    assert "+10.00 %, pasa del umbral de 5.00 %" in mt01["mensaje"]
    for i in INSUMOS:
        a = bs[i.codigo]
        assert Decimal(a["precio_bs"]) == i.precio * 110
        assert Decimal(a["variacion"]) == Decimal("0.1")
        assert "pasa del umbral" in a["mensaje"]


@pytest.mark.parametrize(
    ("umbral", "juicio"),
    [("0.1", "pasa del umbral de 10.00 %"), ("0.1000001", "dentro del umbral de 10.00 %")],
)
def test_umbral_de_la_peticion_frontera_en_la_variacion(cliente, sesion, limpio, umbral, juicio):
    _sembrar_tasas(sesion)
    d = _auditar(cliente, limpio.datos, umbral=umbral).json()
    bs = [a for a in d["alertas"] if a["tipo"] == "USD-Bs"]
    assert len(bs) == len(INSUMOS)
    assert all(juicio in a["mensaje"] for a in bs), [a["mensaje"] for a in bs]


def test_fecha_libro_dada_manda_sobre_la_portada(cliente, limpio) -> None:
    d = _auditar(cliente, limpio.datos, fecha_libro="2026-08-15").json()
    assert d["fecha_libro"] == "2026-08-15"
    assert {a["fecha"] for a in d["alertas"]} == {"2026-08-15"}


def test_otra_version_con_precio_distinto_alerta_por_codigo(cliente, limpio) -> None:
    insumos = tuple(replace(i, precio=Decimal("8")) if i.codigo == "MT-01" else i for i in INSUMOS)
    anterior = construir_libro(siembra=Siembra(insumos=insumos)).datos
    d = _auditar(cliente, limpio.datos, archivos={"anterior": ("version_b1.xlsx", anterior)}).json()
    version = [a for a in d["alertas"] if a["tipo"] == "otra versión"]
    assert [a["codigo"] for a in version] == ["MT-01"]
    assert Decimal(version[0]["variacion"]) == Decimal("0.25")  # (10 − 8) ÷ 8
    assert "version_b1.xlsx" in version[0]["mensaje"]


# --- POST /v1/libros/auditoria: libro con H1 ---


def test_libro_con_h1_f1_con_impacto_calculado_a_mano(cliente, con_h1) -> None:
    r = _auditar(cliente, con_h1.datos)
    assert r.status_code == 200, r.text
    d = r.json()
    impacto_bruto = Decimal("1.59375") * Decimal("1.1") * Decimal("1.1") * 80
    assert impacto_bruto == Decimal("154.275")
    desglose = Decimal("1.59375") * 80
    assert desglose == Decimal("127.50")
    assert _hallazgos(d) == Counter(
        {
            ("F1", "ERROR", "154.28", "corregido"): 1,
            ("L4", "ERROR", "154.28", "corregido"): 1,
            ("L9", "ERROR", "127.50", "corregido"): 2,
            ("R2", "INFO", None, "informado"): 1,
            ("R7", "INFO", None, "informado"): 1,
        }
    )
    f1 = next(h for h in d["hallazgos"] if h["codigo"] == "F1")
    assert f1["celda"] == f"PRESUPUESTO!P{FILA_PRIMERA_PARTIDA + 1}"  # partida 2, columna P.U.
    l4 = next(h for h in d["hallazgos"] if h["codigo"] == "L4")
    assert l4["celda"] == f"APU-02!G{con_h1.filas_apu['APU-02'].cd}"
    assert d["cumple"] is False
    assert d["por_severidad"] == {"ERROR": 4, "INFO": 2}


def test_libro_con_h1_totales_del_libro_y_de_silice(cliente, con_h1) -> None:
    d = _auditar(cliente, con_h1.datos).json()
    # Lo que el libro guarda (con el error) y lo que Silice recalcula (la memoria limpia).
    assert d["totales_libro"] == {
        "SUBSINIVA": "4203.93325",
        "IVATOT": "672.62932",
        "TOTALGEN": "4876.56257",
    }
    assert Decimal(d["totales_libro"]["SUBSINIVA"]) == MEMORIA["SUBSINIVA"] - Decimal("154.275")
    for clave in ("SUBSINIVA", "IVATOT", "TOTALGEN"):
        assert Decimal(d["totales_silice"][clave]) == MEMORIA[clave]


# --- Indicadores (RS2-7, RF-116): actual = libro, meta = Silice, sentido «costo» ---


def _indicadores(d: dict) -> dict[str, tuple[str, str, str, str | None]]:
    return {
        i["clave"]: (i["actual"], i["meta"], i["delta"], i["delta_pct"]) for i in d["indicadores"]
    }


def test_indicadores_del_libro_limpio_no_tienen_variacion(cliente, limpio) -> None:
    d = _auditar(cliente, limpio.datos).json()
    assert [(i["clave"], i["titulo"], i["sentido"]) for i in d["indicadores"]] == [
        ("SUBSINIVA", "Subtotal sin IVA", "costo"),
        ("IVATOT", "IVA", "costo"),
        ("TOTALGEN", "Total general", "costo"),
    ]
    # El libro guarda la memoria (4 358,20825; 697,31332; 5 055,52157) y Silice recalcula los
    # mismos valores con más ceros a la derecha (7 y 9 decimales): Δ = 0 con esos decimales.
    assert _indicadores(d) == {
        "SUBSINIVA": ("4358.20825", "4358.2082500", "0.0000000", "0.00"),
        "IVATOT": ("697.31332", "697.313320000", "0.000000000", "0.00"),
        "TOTALGEN": ("5055.52157", "5055.521570000", "0.000000000", "0.00"),
    }
    for clave, (actual, meta, _, _) in _indicadores(d).items():
        assert actual == d["totales_libro"][clave] and meta == d["totales_silice"][clave]
        assert Decimal(actual) == Decimal(meta) == MEMORIA[clave]


def test_indicadores_con_sobreprecio_sembrado(cliente) -> None:
    """P guardado de APU-01 = 15 (Silice: 14,486725). Cuenta a mano:
    monto del libro 120 × 15 = 1 800; SUBSINIVA del libro 1 800 + 2 416,975 + 202,82625 =
    4 419,80125; Δ = 120 × (15 − 14,486725) = 120 × 0,513275 = 61,593. IVA 0,16 × 4 419,80125 =
    707,1682; Δ = 0,16 × 61,593 = 9,85488. Total 4 419,80125 + 707,1682 = 5 126,96945;
    Δ = 61,593 + 9,85488 = 71,44788. Los tres Δ guardan la misma proporción (el IVA es el 16 %
    de cada subtotal): Δ% = 61,593 ÷ 4 358,20825 × 100, y como 4 358,20825 × 0,01405 = 61,23283
    ≤ 61,593 < 61,66865 = 4 358,20825 × 0,01415, cae en [1,405 ; 1,415): 1,41."""
    sobreprecio = construir_libro(siembra=Siembra(p_guardado={1: Decimal("15")}))
    d = _auditar(cliente, sobreprecio.datos).json()
    meta = MEMORIA["SUBSINIVA"]
    assert meta * Decimal("0.01405") <= Decimal("61.593") < meta * Decimal("0.01415")
    assert _indicadores(d) == {
        "SUBSINIVA": ("4419.80125", "4358.2082500", "61.5930000", "1.41"),
        "IVATOT": ("707.1682", "697.313320000", "9.854880000", "1.41"),
        "TOTALGEN": ("5126.96945", "5055.521570000", "71.447880000", "1.41"),
    }
    assert Decimal("120") * (Decimal("15") - Decimal("14.486725")) == Decimal("61.593")
    assert Decimal("0.16") * Decimal("61.593") == Decimal("9.85488")


def test_indicadores_con_h1_bajo_el_costo_de_silice(cliente, con_h1) -> None:
    """H1: el libro declara 154,275 menos sin IVA (cabecera del módulo). Δ IVA = 0,16 × −154,275
    = −24,684; Δ total = −154,275 − 24,684 = −178,959. Δ% = −154,275 ÷ 4 358,20825 × 100, y como
    4 358,20825 × 0,03535 = 154,06266 ≤ 154,275 < 154,49848 = 4 358,20825 × 0,03545: −3,54."""
    d = _auditar(cliente, con_h1.datos).json()
    meta = MEMORIA["SUBSINIVA"]
    assert meta * Decimal("0.03535") <= Decimal("154.275") < meta * Decimal("0.03545")
    assert _indicadores(d) == {
        "SUBSINIVA": ("4203.93325", "4358.2082500", "-154.2750000", "-3.54"),
        "IVATOT": ("672.62932", "697.313320000", "-24.684000000", "-3.54"),
        "TOTALGEN": ("4876.56257", "5055.521570000", "-178.959000000", "-3.54"),
    }


def test_libro_y_pdf_simple_juntos_suman_l10_informado(cliente, limpio) -> None:
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    d = _auditar(cliente, limpio.datos, archivos={"pdf": ("entregado.pdf", pdf)}).json()
    assert _hallazgos(d) == Counter(
        {
            ("R2", "INFO", None, "informado"): 1,
            ("R7", "INFO", None, "informado"): 1,
            ("L10", "ERROR", "1.65", "informado"): 1,
        }
    )
    assert len(d["metadatos"]["sha256_pdf"]) == 64


# --- Entrada: fechas, umbral, extensiones (422 y 415) ---


@pytest.mark.parametrize("ruta", RUTAS_DEL_LIBRO)
def test_fecha_devolucion_ausente_o_vacia_422(cliente, limpio, ruta) -> None:
    """Ausente o vacía (FastAPI trata el campo de formulario vacío como ausente): 422 de la
    validación de FastAPI, que señala el campo."""
    for valor in (None, ""):
        r = _post(cliente, ruta, limpio.datos, fecha_devolucion=valor)
        assert r.status_code == 422, (valor, r.text)
        assert any(e["loc"] == ["body", "fecha_devolucion"] for e in r.json()["detail"])


def test_fecha_devolucion_en_blanco_o_mal_escrita_422(cliente, limpio) -> None:
    for valor, fragmento in (
        ("   ", "falta 'fecha_devolucion'"),
        ("13/10/2026", "'fecha_devolucion' no es una fecha ISO válida"),
        ("2026-02-30", "'fecha_devolucion' no es una fecha ISO válida"),
        ("ayer", "'fecha_devolucion' no es una fecha ISO válida"),
    ):
        r = _auditar(cliente, limpio.datos, fecha_devolucion=valor)
        assert r.status_code == 422, (valor, r.text)
        assert fragmento in r.json()["detalle"], valor


def test_fecha_libro_mal_escrita_422(cliente, limpio) -> None:
    r = _auditar(cliente, limpio.datos, fecha_libro="julio 2026")
    assert r.status_code == 422
    assert "'fecha_libro' no es una fecha ISO válida" in r.json()["detalle"]


def test_umbral_frontera_0_y_1_fuera_y_no_decimal_422(cliente, limpio) -> None:
    """0 < umbral < 1: los dos extremos, fuera de rango, texto, NaN e infinito dan 422."""
    for umbral in ("0", "1", "0.0", "1.0", "-0.05", "1.5", "texto", "NaN", "Infinity", "5%"):
        r = _auditar(cliente, limpio.datos, umbral=umbral)
        assert r.status_code == 422, (umbral, r.text)
        mensaje = r.json()["detalle"]
        assert "'umbral' debe ser un decimal con punto mayor que 0 y menor que 1" in mensaje


def test_umbral_dentro_del_rango_200(cliente, limpio) -> None:
    for umbral in ("0.05", "0.0001", "0.9999"):
        assert _auditar(cliente, limpio.datos, umbral=umbral).status_code == 200, umbral


@pytest.mark.parametrize("ruta", RUTAS_DEL_LIBRO)
def test_extension_del_libro_no_xlsx_415(cliente, limpio, ruta) -> None:
    for nombre in ("libro.xlsm", "libro.csv", "libro.xls", ".xlsx", "libro"):
        r = _post(cliente, ruta, limpio.datos, nombre=nombre)
        assert r.status_code == 415, (nombre, r.text)
        assert "Solo se aceptan libros de Excel .xlsx sin macros." in r.json()["detalle"]


def test_extension_en_mayusculas_se_acepta(cliente, limpio) -> None:
    r = _post(cliente, "/v1/libros/auditoria", limpio.datos, nombre="LIBRO.XLSX")
    assert r.status_code == 200, r.text


def test_pdf_y_anterior_con_extension_equivocada_415(cliente, limpio) -> None:
    r = _auditar(cliente, limpio.datos, archivos={"pdf": ("entregado.txt", b"%PDF-1.4")})
    assert r.status_code == 415
    assert "'pdf' debe ser un archivo .pdf" in r.json()["detalle"]
    r = _auditar(cliente, limpio.datos, archivos={"anterior": ("b1.csv", limpio.datos)})
    assert r.status_code == 415
    assert "'anterior' debe ser un archivo .xlsx" in r.json()["detalle"]


# --- Rechazos de la guardia y del lector (422 con el mensaje para el usuario) ---


def test_bytes_que_no_son_zip_rechazados_por_la_guardia_422(cliente) -> None:
    for ruta in RUTAS_DEL_LIBRO:
        r = _post(cliente, ruta, b"esto no es un libro de Excel", nombre="falso.xlsx")
        assert r.status_code == 422, (ruta, r.text)
        assert r.json() == {
            "detalle": "El archivo «falso.xlsx» no es un libro .xlsx válido (está dañado o no es "
            "de Excel)."
        }


def test_libro_sin_hoja_presupuesto_422(cliente, limpio) -> None:
    wb = openpyxl.load_workbook(io.BytesIO(limpio.datos))
    del wb["PRESUPUESTO"]
    buf = io.BytesIO()
    wb.save(buf)
    r = _post(cliente, "/v1/libros/auditoria", buf.getvalue(), nombre="sin_presupuesto.xlsx")
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "El libro «sin_presupuesto.xlsx» no tiene la hoja PRESUPUESTO: no parece un "
        "presupuesto de la plantilla de la empresa."
    }


def test_pdf_adjunto_que_no_es_pdf_422(cliente, limpio) -> None:
    r = _auditar(cliente, limpio.datos, archivos={"pdf": ("entregado.pdf", b"no soy un pdf")})
    assert r.status_code == 422
    assert r.json() == {
        "detalle": "El archivo «entregado.pdf» no es un PDF (no tiene la cabecera %PDF-)."
    }


def test_cuerpo_de_mas_de_20_mib_413_y_en_el_limite_no(cliente) -> None:
    cabecera = {"content-type": "multipart/form-data; boundary=x"}
    r = cliente.post("/v1/libros/auditoria", content=b"0" * (LIMITE_CUERPO + 1), headers=cabecera)
    assert r.status_code == 413
    r = cliente.post("/v1/libros/auditoria", content=b"0" * LIMITE_CUERPO, headers=cabecera)
    # En el límite el tope deja pasar el cuerpo; lo rechaza después el lector de multipart
    # (400: el cuerpo no trae el separador declarado).
    assert r.status_code != 413
    assert r.status_code == 400


# --- Fallo interno: 500 con mensaje fijo y sin el texto de la excepción ---

SECRETO = "detalle-interno-que-no-debe-salir C:\\ruta\\secreta"


def test_fallo_interno_al_procesar_500_mensaje_fijo(cliente, limpio, monkeypatch, caplog) -> None:
    import api.rutas.libros as rutas

    def _revienta(*_a, **_k):
        raise RuntimeError(SECRETO)

    monkeypatch.setattr(rutas, "procesar_libro", _revienta)
    for ruta in RUTAS_DEL_LIBRO:
        r = _post(cliente, ruta, limpio.datos)
        assert r.status_code == 500, ruta
        assert r.json() == {"detalle": "El libro no se pudo interpretar."}
        assert "detalle-interno" not in r.text and "secreta" not in r.text
        assert "RuntimeError" not in r.text
    # El detalle va solo al registro del servidor.
    assert any("RuntimeError" in m for m in caplog.messages)


def test_fallo_interno_al_devolver_500_mensaje_fijo(cliente, limpio, monkeypatch) -> None:
    import api.rutas.libros as rutas

    def _revienta(*_a, **_k):
        raise RuntimeError(SECRETO)

    monkeypatch.setattr(rutas, "devolver", _revienta)
    r = _post(cliente, "/v1/libros/devolucion", limpio.datos)
    assert r.status_code == 500
    assert r.json() == {"detalle": "El libro no se pudo interpretar."}
    assert "detalle-interno" not in r.text


def test_fallo_interno_del_pdf_500_mensaje_fijo(cliente, monkeypatch) -> None:
    import api.rutas.libros as rutas

    def _revienta(*_a, **_k):
        raise RuntimeError(SECRETO)

    monkeypatch.setattr(rutas, "auditar_pdf_simple", _revienta)
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("p.pdf", pdf)})
    assert r.status_code == 500
    assert r.json() == {"detalle": "El PDF no se pudo interpretar."}
    assert "detalle-interno" not in r.text


# --- POST /v1/libros/devolucion ---


def _libro_devuelto(r) -> openpyxl.Workbook:
    return openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)


def test_devolucion_xlsx_con_nombre_de_descarga_y_hojas_de_silice(cliente, limpio) -> None:
    r = _post(cliente, "/v1/libros/devolucion", limpio.datos, nombre="Mi libro ñ.xlsx")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == TIPO_XLSX
    # NFKD quita la tilde de la ñ; el resto se conserva y se añade «-silice».
    assert r.headers["content-disposition"] == 'attachment; filename="Mi libro n-silice.xlsx"'
    assert len(r.headers["x-silice-sha256-origen"]) == 64
    wb = _libro_devuelto(r)
    hojas = wb.sheetnames
    assert {"AUDITORÍA", "TRAZABILIDAD", "ALERTAS USD-Bs"} <= set(hojas)
    assert "AUX" not in hojas
    assert set(hojas) == (set(limpio.hojas) - {"AUX"}) | {
        "AUDITORÍA",
        "TRAZABILIDAD",
        "ALERTAS USD-Bs",
    }


def test_devolucion_nombre_de_descarga_sin_comillas_ni_rutas(cliente, limpio) -> None:
    for nombre, descarga in (
        ("Presupuesto; Edición #2 (final).xlsx", "Presupuesto_ Edicion _2 _final_-silice.xlsx"),
        ("../../etc/passwd.xlsx", "passwd-silice.xlsx"),
        ("C:\\obras\\Presupuesto B-2.xlsx", "Presupuesto B-2-silice.xlsx"),
        ("ñ.xlsx", "n-silice.xlsx"),
        ("«».xlsx", "libro-silice.xlsx"),  # sin ASCII: queda vacío
        ("....xlsx", "libro-silice.xlsx"),
    ):
        r = _post(cliente, "/v1/libros/devolucion", limpio.datos, nombre=nombre)
        assert r.status_code == 200, (nombre, r.text)
        assert r.headers["content-disposition"] == f'attachment; filename="{descarga}"'


def test_devolucion_nombre_con_comillas_y_saltos_no_rompe_la_cabecera(cliente, limpio) -> None:
    """El cliente HTTP codifica `"`, CR y LF del nombre (%22, %0D, %0A); llegue como llegue, la
    cabecera solo lleva [A-Za-z0-9 ._-] entre sus comillas."""
    r = _post(cliente, "/v1/libros/devolucion", limpio.datos, nombre='a"b\r\nc.xlsx')
    assert r.status_code == 200, r.text
    valor = r.headers["content-disposition"]
    prefijo = 'attachment; filename="'
    assert valor.startswith(prefijo) and valor.endswith('-silice.xlsx"')
    assert re.fullmatch(r"[A-Za-z0-9 ._-]+", valor[len(prefijo) : -1]), valor


def test_devolucion_p_de_presupuesto_igual_a_la_memoria(cliente, limpio) -> None:
    wb = _libro_devuelto(_post(cliente, "/v1/libros/devolucion", limpio.datos))
    ws = wb["PRESUPUESTO"]
    for k, hoja in enumerate(("APU-01", "APU-02", "APU-03")):
        fila = FILA_PRIMERA_PARTIDA + k
        assert fila == limpio.filas_partida[hoja]
        valor = Decimal(str(ws[f"P{fila}"].value))
        assert abs(valor - MEMORIA["componentes"][hoja]["PU"]) <= TOL_CELDA, (hoja, valor)


def test_devolucion_con_h1_p_corregido_y_f1_en_auditoria(cliente, con_h1) -> None:
    wb = _libro_devuelto(_post(cliente, "/v1/libros/devolucion", con_h1.datos))
    fila = FILA_PRIMERA_PARTIDA + 1
    valor = Decimal(str(wb["PRESUPUESTO"][f"P{fila}"].value))
    # El libro guardaba 30,2121875 − 1,9284375 = 28,28375; Silice devuelve el de la memoria.
    assert abs(valor - Decimal("30.2121875")) <= TOL_CELDA
    textos = {
        str(c.value) for fila_ in wb["AUDITORÍA"].iter_rows() for c in fila_ if c.value is not None
    }
    assert "F1" in textos and "L4" in textos


# --- POST /v1/libros/pdf ---


def test_pdf_simple_l10_aritmetica_de_fila_impacto_1_65(cliente) -> None:
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("presupuesto_001.pdf", pdf)})
    assert r.status_code == 200, r.text
    d = r.json()
    assert [(h["codigo"], h["severidad"], h["impacto"], h["accion"]) for h in d["hallazgos"]] == [
        ("L10", "ERROR", "1.65", "informado")
    ]
    h = d["hallazgos"][0]
    assert h["descripcion"].startswith("aritmética de fila:")
    assert Decimal("1446.65") - Decimal(5) * Decimal("289.00") == Decimal("1.65")
    assert d["cumple"] is False
    assert d["por_severidad"] == {"ERROR": 1}
    assert d["renglones_presupuesto"] == 1 and d["renglones_computos"] == 0
    assert Decimal(d["total_impreso"]) == Decimal("1446.65")
    assert d["total_computos"] is None
    assert d["pdf"]["nombre"] == "presupuesto_001.pdf"
    assert d["pdf"]["numero"] == "001" and d["pdf"]["fecha"] == "18/05/2026"
    assert len(d["pdf"]["sha256"]) == 64


def test_pdf_simple_que_cuadra_cumple_sin_hallazgos(cliente) -> None:
    bien = ("1", "Friso liso (ficticio)", "m2", "5", "289,00", "1445,00")
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("p.pdf", _pdf_simple([bien], "1445,00"))})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["hallazgos"] == [] and d["cumple"] is True and d["por_severidad"] == {}


def test_pdf_sin_tablas_422(cliente) -> None:
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("carta.pdf", _pdf_sin_tablas())})
    assert r.status_code == 422, r.text
    assert r.json()["detalle"].startswith(
        "El PDF «carta.pdf» no tiene una tabla de cómputos ni de presupuesto"
    )


def test_pdf_con_extension_equivocada_415_y_bytes_ajenos_422(cliente) -> None:
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("presupuesto.docx", pdf)})
    assert r.status_code == 415
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("p.pdf", b"PK\x03\x04 no es un pdf")})
    assert r.status_code == 422
    assert r.json() == {"detalle": "El archivo «p.pdf» no es un PDF (no tiene la cabecera %PDF-)."}


def test_pdf_tope_de_paginas_60_pasa_61_no(cliente) -> None:
    sesenta = _pdf_simple([RENGLON_MAL], "1446,65", paginas_de_relleno=59)
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("p60.pdf", sesenta)})
    assert r.status_code == 200, r.text
    sesenta_y_una = _pdf_simple([RENGLON_MAL], "1446,65", paginas_de_relleno=60)
    r = cliente.post("/v1/libros/pdf", files={"pdf": ("p61.pdf", sesenta_y_una)})
    assert r.status_code == 422
    assert r.json() == {
        "detalle": "El PDF «p61.pdf» tiene 61 páginas y el máximo es 60. No parece un presupuesto."
    }


# --- Determinismo y nada guardado (F-D9) ---


def test_dos_peticiones_iguales_dan_el_mismo_json(cliente, con_h1) -> None:
    a = _auditar(cliente, con_h1.datos)
    b = _auditar(cliente, con_h1.datos)
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    p1 = cliente.post("/v1/libros/pdf", files={"pdf": ("p.pdf", pdf)}).json()
    p2 = cliente.post("/v1/libros/pdf", files={"pdf": ("p.pdf", pdf)}).json()
    assert p1 == p2


def test_nada_se_guarda_en_la_base_ni_se_escribe_en_disco(
    cliente, sesion, con_h1, escrituras
) -> None:
    pdf = _pdf_simple([RENGLON_MAL], "1446,65")
    antes = _filas_por_tabla(sesion)
    escrituras.clear()
    assert _auditar(cliente, con_h1.datos, archivos={"pdf": ("e.pdf", pdf)}).status_code == 200
    assert _post(cliente, "/v1/libros/devolucion", con_h1.datos).status_code == 200
    assert cliente.post("/v1/libros/pdf", files={"pdf": ("p.pdf", pdf)}).status_code == 200
    assert escrituras == []
    assert _filas_por_tabla(sesion) == antes
    assert not sesion.new and not sesion.dirty and not sesion.deleted
