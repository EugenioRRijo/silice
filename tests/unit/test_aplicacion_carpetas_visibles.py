"""`aplicacion.casos.carpetas_visibles` (anexo A.4 del plan de desenredo): que carpetas lista una
cuenta en las rutas `/v1/obras/*/todas`. Antes vivia en `api/rutas/obras.py`; la ruta solo le pasa
la carpeta de la empresa, la abierta y si la cuenta puede abrir carpetas. Archivos vacios con
nombres ficticios; `listar_casos` se reemplaza por la lista de la prueba."""

from __future__ import annotations

from pathlib import Path

import pytest

from aplicacion import casos


@pytest.fixture
def carpetas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    nombres = ("empresa.db", "Obra Norte.db", "Obra Sur.db", "Demostración.db")
    rutas = {nombre: tmp_path / nombre for nombre in nombres}
    for ruta in rutas.values():
        ruta.touch()
    monkeypatch.setattr(casos, "listar_casos", lambda: list(rutas.values()))
    return rutas


def test_quien_abre_carpetas_ve_la_empresa_y_las_demas_sin_la_demostracion(carpetas) -> None:
    empresa = carpetas["empresa.db"]
    actual, visibles = casos.carpetas_visibles(empresa, None, ve_todas=True)
    assert actual is None
    assert visibles == [
        (None, empresa),
        ("Obra Norte.db", carpetas["Obra Norte.db"]),
        ("Obra Sur.db", carpetas["Obra Sur.db"]),
    ]


def test_la_empresa_escrita_de_otra_forma_sigue_siendo_la_empresa(carpetas, tmp_path) -> None:
    (tmp_path / "x").mkdir()
    rodeo = tmp_path / "x" / ".." / "empresa.db"
    actual, visibles = casos.carpetas_visibles(carpetas["empresa.db"], rodeo, ve_todas=False)
    assert (actual, visibles) == (None, [(None, carpetas["empresa.db"])])


def test_con_la_demostracion_abierta_solo_se_lista_ella(carpetas) -> None:
    demo = carpetas["Demostración.db"]
    for ve_todas in (True, False):
        assert casos.carpetas_visibles(carpetas["empresa.db"], demo, ve_todas=ve_todas) == (
            "Demostración.db",
            [("Demostración.db", demo)],
        )


def test_sin_abrir_carpetas_solo_la_abierta(carpetas) -> None:
    norte = carpetas["Obra Norte.db"]
    assert casos.carpetas_visibles(carpetas["empresa.db"], norte, ve_todas=False) == (
        "Obra Norte.db",
        [("Obra Norte.db", norte)],
    )
    assert casos.carpetas_visibles(None, None, ve_todas=False) == (None, [])
