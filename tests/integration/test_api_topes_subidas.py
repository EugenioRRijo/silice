"""Listas de precios y presupuestos subidos con celdas lejanas (acta del árbitro de los topes,
NOTA 7; ESTADO §4.10 b).

`core.catalog.precios.leer_tabla` recorre cada hoja en solo lectura sin tope: una hoja que no
declara su `<dimension>` y escribe en A1048576 le hace recorrer un millón de filas, y una fila en
XFD le entrega 16.384 valores por fila. El núcleo no se toca: la API acota antes de llamarlo, en
`api.rutas.listas.comprobar_libro_legible`, con los mismos topes del lector del libro conocido
(`lector.filas_acotadas`: 20.000 filas y 100 columnas por hoja, y `MAX_CELDAS_LIBRO` celdas por
pasada en el libro entero) y el mismo aviso.

Casos construidos a mano con openpyxl en `tmp_path` (ningún libro real, NORMAS §1). Dos formas de
la hoja hostil: con una `<dimension>` falsa que declara solo lo de antes (la guardia la deja
pasar) y sin `<dimension>` (la que hacía recorrer el millón de filas). Fronteras exactas: la fila
20.000 y la columna CV (100) se aceptan; la 20.001 y la CW (101), no.
"""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pytest
from openpyxl.worksheet._read_only import ReadOnlyWorksheet
from sqlalchemy import func, select

from adapters.hoja_empresa import lector
from api.rutas.listas import comprobar_libro_legible
from core import models
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.libro_apu_por_hoja import con_celdas

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SIGUE = (
    "Sílice lee de cada hoja hasta 20.000 filas y 100 columnas (de la A a la CV). Se rechaza por "
    "seguridad: borre lo que sobra al final de la hoja y guárdelo de nuevo."
)
FILAS = "tiene filas con datos o con formato más allá de la 20.000"
FORMAS = {"dimension_falsa": {}, "sin_dimension": {"sin_dimension": True}}


def _ancha(fila: int, columna: str) -> str:
    return (
        f"la fila {fila} tiene celdas con datos o con formato hasta la columna {columna}, "
        "más allá de la CV"
    )


def _rechazo(nombre: str, hoja: str, donde: str) -> str:
    """El 422 de `comprobar_libro_legible`: el aviso del lector tal cual, que ya nombra el libro y
    la hoja. Sin «no se puede leer como libro de Excel»: el libro se lee, lo que pasa es que tiene
    algo escrito más allá de los topes (simulación de las decisiones, 2026-11-12)."""
    return f"El libro «{nombre}», hoja «{hoja}»: {donde}. {SIGUE}"


def _lista(celdas: dict[str, object] | None = None, **forma) -> bytes:
    """Una lista de precios ficticia (encabezados de UC-02 y un renglón) con `celdas` añadidas."""
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Lista"
    hoja.append(["tipo", "insumo", "unidad", "precio"])
    hoja.append(["material", "Aditivo ficticio", "lt", "12"])
    salida = io.BytesIO()
    libro.save(salida)
    if celdas is None:
        return salida.getvalue()
    return con_celdas(salida.getvalue(), "Lista", celdas, **forma)


@pytest.fixture
def filas_entregadas(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Cuenta las filas que openpyxl entrega en solo lectura (las del núcleo incluidas)."""
    cuenta = [0]
    original = ReadOnlyWorksheet.iter_rows

    def contando(self, *args, **kwargs):
        for fila in original(self, *args, **kwargs):
            cuenta[0] += 1
            yield fila

    monkeypatch.setattr(ReadOnlyWorksheet, "iter_rows", contando)
    return cuenta


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


# --- comprobar_libro_legible: los topes y sus fronteras --------------------------------------


@pytest.mark.parametrize("forma", FORMAS)
@pytest.mark.parametrize(
    ("celdas", "donde"),
    [
        ({"A20001": "fin ficticio"}, FILAS),
        ({"A1048576": "fin ficticio"}, FILAS),
        ({"CW1": "y"}, _ancha(1, "CW")),
        ({f"XFD{fila}": "y" for fila in range(3, 2003)}, _ancha(3, "XFD")),
    ],
    ids=["A20001", "A1048576", "CW1", "XFD"],
)
def test_una_celda_lejana_hace_ilegible_la_lista(
    tmp_path: Path, filas_entregadas: list[int], celdas: dict, donde: str, forma: str
):
    ruta = tmp_path / "lista_hostil.xlsx"
    ruta.write_bytes(_lista(celdas, **FORMAS[forma]))
    with pytest.raises(ValueError) as error:
        comprobar_libro_legible(ruta)
    assert str(error.value) == _rechazo("lista_hostil.xlsx", "Lista", donde)
    assert filas_entregadas[0] <= 20_001, f"openpyxl entregó {filas_entregadas[0]:,} filas"


def test_la_lista_en_el_tope_exacto_es_legible(tmp_path: Path):
    """CV20000: la fila 20.000 y la columna 100. Su `<dimension>` (A1:CV20000, 2.000.000 de
    celdas) es la que la guardia todavía acepta."""
    ruta = tmp_path / "lista_tope.xlsx"
    ruta.write_bytes(_lista({"CV20000": "y"}, dimension_de_antes=False))
    assert comprobar_libro_legible(ruta) is None


def test_el_tope_de_celdas_del_libro_suma_todas_las_hojas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """La cuenta de `MAX_CELDAS_LIBRO` es del libro entero, no de cada hoja: dos hojas de 2 × 4
    celdas (8 + 8 = 16) caben en un tope de 16 y no en uno de 15."""
    libro = openpyxl.Workbook()
    libro.active.title = "Lista"
    for hoja in (libro.active, libro.create_sheet("Otra")):
        hoja.append(["tipo", "insumo", "unidad", "precio"])
        hoja.append(["material", "Aditivo ficticio", "lt", "12"])
    ruta = tmp_path / "dos_hojas.xlsx"
    libro.save(ruta)
    monkeypatch.setattr(lector, "MAX_CELDAS_LIBRO", 16)
    assert comprobar_libro_legible(ruta) is None
    monkeypatch.setattr(lector, "MAX_CELDAS_LIBRO", 15)
    with pytest.raises(ValueError) as error:
        comprobar_libro_legible(ruta)
    assert str(error.value) == (
        "El libro «dos_hojas.xlsx» tiene más de 15 celdas con datos o con formato entre sus "
        "hojas. Se rechaza por seguridad: quite las hojas o las filas que sobran y guárdelo de "
        "nuevo."
    )


def test_las_filas_de_hueco_tambien_cuentan_para_el_tope_del_libro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Una celda en A50 hace que openpyxl entregue 49 filas vacías antes: no sumaban nada, así que
    1.000 hojas con una celda en A20000 pasaban el tope del libro tras 20 millones de filas (12 s;
    agente de los índices, 2026-11-12). Cada fila entregada cuenta como una celda por lo menos:
    tres hojas de 50 filas (150) caben en un tope de 150 y no en uno de 149."""
    libro = openpyxl.Workbook()
    libro.active.title = "H1"
    for hoja in (libro.active, libro.create_sheet("H2"), libro.create_sheet("H3")):
        hoja["A50"] = "dato ficticio"
    ruta = tmp_path / "huecos.xlsx"
    libro.save(ruta)
    monkeypatch.setattr(lector, "MAX_CELDAS_LIBRO", 150)
    assert comprobar_libro_legible(ruta) is None
    monkeypatch.setattr(lector, "MAX_CELDAS_LIBRO", 149)
    with pytest.raises(ValueError) as error:
        comprobar_libro_legible(ruta)
    assert "tiene más de 149 celdas con datos o con formato entre sus hojas" in str(error.value)


# --- por HTTP: listas de precios y presupuesto de un tercero ---------------------------------


def _subir_lista(cliente, datos: bytes, ruta: str = "/listas-precios"):
    campos = {"nombre": "Hostil", "moneda": linea_base.MONEDA, "fecha_vigencia": "2026-06-01"}
    return cliente.post(
        ruta,
        files={"archivo": ("lista_hostil.xlsx", datos, TIPO_XLSX)},
        data=campos if ruta == "/listas-precios" else {},
    )


@pytest.mark.parametrize("forma", FORMAS)
def test_cargar_una_lista_con_una_celda_lejana_es_422_sin_escribir_nada(
    cliente, sesion, filas_entregadas: list[int], forma: str
):
    antes = (_contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios))
    r = _subir_lista(cliente, _lista({"A1048576": "fin ficticio"}, **FORMAS[forma]))
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == _rechazo("lista_hostil.xlsx", "Lista", FILAS)
    assert filas_entregadas[0] <= 20_001, f"openpyxl entregó {filas_entregadas[0]:,} filas"
    assert (_contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios)) == antes


def test_la_vista_previa_de_una_lista_con_una_celda_lejana_trae_el_motivo(
    cliente, filas_entregadas: list[int]
):
    r = _subir_lista(
        cliente,
        _lista({"A1048576": "fin ficticio"}, sin_dimension=True),
        "/listas-precios/vista-previa",
    )
    assert r.status_code == 200, r.text
    assert r.json() == {
        "desconocidos": [],
        "motivo": _rechazo("lista_hostil.xlsx", "Lista", FILAS),
    }
    assert filas_entregadas[0] <= 20_001, f"openpyxl entregó {filas_entregadas[0]:,} filas"


def test_importar_un_presupuesto_con_una_celda_lejana_es_422_sin_escribir_nada(
    cliente, sesion, tmp_path: Path, filas_entregadas: list[int]
):
    from tests.fixtures.presupuesto_tabular import escribir_presupuesto_tabular

    creado = cliente.post("/proyectos", json={"nombre": "Tercero hostil", "dominio": "civil"})
    assert creado.status_code == 201, creado.text
    limpio = escribir_presupuesto_tabular(tmp_path).read_bytes()
    datos = con_celdas(limpio, "APU", {"A1048576": "fin ficticio"}, sin_dimension=True)
    antes = (_contar(sesion, models.Presupuesto), _contar(sesion, models.ListaPrecios))
    r = cliente.post(
        "/presupuestos/importar",
        files={"archivo": ("tercero_hostil.xlsx", datos, TIPO_XLSX)},
        data={"proyecto": "Tercero hostil"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == _rechazo("tercero_hostil.xlsx", "APU", FILAS)
    # las hojas anteriores del formato (Datos, Presupuesto) se recorren antes: unas pocas filas más
    assert filas_entregadas[0] <= 20_001 + 100, f"openpyxl entregó {filas_entregadas[0]:,} filas"
    assert (_contar(sesion, models.Presupuesto), _contar(sesion, models.ListaPrecios)) == antes
