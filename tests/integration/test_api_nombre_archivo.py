"""Seguridad de las rutas que reciben un archivo (QA de GC6, H4): el nombre lo manda el cliente.

`POST /listas-precios`, `POST /presupuestos/importar` y `POST /computos/{dominio}` guardan el
archivo en un directorio temporal con su nombre. Un nombre con `..` o una ruta absoluta no puede
escribir fuera de ese directorio: la ruta responde como con un nombre normal y, pase lo que pase,
no queda nada fuera. Las pruebas ponen la raiz de los temporales en `tmp_path` y comprueban que
al terminar no ha quedado ningun archivo en ella (los directorios temporales se borran). Ningun
archivo se escribe en `data/`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import UploadFile

from api.archivos import guardar_subida
from tests.fixtures.presupuesto_tabular import escribir_presupuesto_tabular

RAIZ = Path(__file__).resolve().parents[2]
TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PROYECTO = "Auditoria del drenaje de un tercero"


@pytest.fixture
def raiz_temporal(tmp_path, monkeypatch) -> Path:
    """La raiz donde `tempfile` crea sus directorios: `../x` desde uno de ellos cae aqui."""
    raiz = tmp_path / "raiz_temporal"
    raiz.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(raiz))
    return raiz


def _nombres(raiz: Path) -> list[str]:
    return [str(p) for p in raiz.rglob("*")]


def _con_nombres_hostiles(raiz: Path, extension: str) -> list[str]:
    return [f"../fuera{extension}", str(raiz / f"absoluto{extension}")]


@pytest.mark.parametrize("indice", [0, 1], ids=["relativo-con-punto-punto", "absoluto"])
def test_cargar_una_lista_con_nombre_hostil_no_escribe_fuera(
    cliente, raiz_temporal, tmp_path, indice
):
    nombre = _con_nombres_hostiles(raiz_temporal, ".csv")[indice]
    contenido = (RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv").read_bytes()

    r = cliente.post(
        "/listas-precios",
        files={"archivo": (nombre, contenido, "text/csv")},
        data={"nombre": "Lista hostil", "moneda": "USD", "fecha_vigencia": "2026-06-01"},
    )

    assert r.status_code == 201, r.text
    assert _nombres(raiz_temporal) == []


@pytest.mark.parametrize("indice", [0, 1], ids=["relativo-con-punto-punto", "absoluto"])
def test_importar_un_presupuesto_con_nombre_hostil_no_escribe_fuera(
    cliente, raiz_temporal, tmp_path, indice
):
    assert cliente.post("/proyectos", json={"nombre": PROYECTO, "dominio": "civil"}).status_code
    nombre = _con_nombres_hostiles(raiz_temporal, ".xlsx")[indice]
    contenido = escribir_presupuesto_tabular(tmp_path).read_bytes()

    r = cliente.post(
        "/presupuestos/importar",
        files={"archivo": (nombre, contenido, TIPO_XLSX)},
        data={"proyecto": PROYECTO},
    )

    assert r.status_code == 201, r.text
    assert _nombres(raiz_temporal) == []


@pytest.mark.parametrize("indice", [0, 1], ids=["relativo-con-punto-punto", "absoluto"])
def test_computar_con_nombre_hostil_no_escribe_fuera(cliente, raiz_temporal, indice):
    nombre = _con_nombres_hostiles(raiz_temporal, ".csv")[indice]
    contenido = (RAIZ / "data" / "samples" / "industrial" / "activos_planta.csv").read_bytes()

    r = cliente.post("/computos/industrial", files={"archivo": (nombre, contenido, "text/csv")})

    assert r.status_code == 200, r.text
    assert r.json()
    assert _nombres(raiz_temporal) == []


@pytest.mark.parametrize("nombre", [None, "", ".", ".."])
def test_un_nombre_sin_archivo_utilizable_se_rechaza(tmp_path, nombre):
    import io

    subida = UploadFile(file=io.BytesIO(b"x"), filename=nombre)

    with pytest.raises(ValueError, match="nombre utilizable"):
        guardar_subida(tmp_path, subida)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("nombre", ["../../fuera.csv", "a/b/c.csv", "{absoluto}"])
def test_solo_cuenta_el_ultimo_componente_del_nombre(tmp_path, nombre):
    """El nombre se conserva por su extension, pero solo su ultimo componente: aqui tambien la
    ruta absoluta, que una prueba por HTTP no puede garantizar (el cliente y el analizador del
    multipart pueden recortarla antes)."""
    import io

    carpeta = tmp_path / "carpeta"
    carpeta.mkdir()
    nombre = nombre.format(absoluto=str(tmp_path / "otra" / "absoluta.csv"))
    subida = UploadFile(file=io.BytesIO(b"x"), filename=nombre)

    ruta = guardar_subida(carpeta, subida)

    assert ruta.parent == carpeta
    assert ruta.name == Path(nombre).name
    assert ruta.read_bytes() == b"x"
    assert [p.name for p in tmp_path.rglob("*") if p.is_file()] == [ruta.name]
