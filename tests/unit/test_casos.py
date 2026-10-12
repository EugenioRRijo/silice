"""Casos en la carpeta de datos (RV-5; spec S5 §6.6): lista, nombres seguros y rutas rechazadas sin
tocar el disco (RF-96 e)."""

from __future__ import annotations

from pathlib import Path

import pytest

from operacion.base_datos import (
    BaseIlegible,
    BaseMasNueva,
    Destino,
    RutaDeCasoRechazada,
    crear_caso,
    leer_estado,
    listar_casos,
    resolver_caso,
    revision_head,
    sanear_nombre,
    subir_caso,
)
from tests.fixtures import bases_prueba

RECHAZADAS = [
    r"\\equipo\x\a.db",
    "//equipo/x/a.db",
    r"C:\x.db",
    "C:x.db",
    "/etc/x.db",
    "../x.db",
    r"casos\..\x.db",
    "sub/x.db",
    "a:b.db",
    "nul.db",
    "CON",
    "",
    "   ",
]


def test_la_lista_trae_solo_los_db_de_la_carpeta_en_orden(tmp_path: Path) -> None:
    carpeta = tmp_path / "casos"
    carpeta.mkdir()
    for nombre in ("b.db", "A.db", "notas.txt", "c.db.migrando"):
        (carpeta / nombre).write_bytes(b"")
    (carpeta / "sub.db").mkdir()
    assert [ruta.name for ruta in listar_casos(carpeta)] == ["A.db", "b.db"]


def test_sin_carpeta_la_lista_es_vacia_y_no_la_crea(tmp_path: Path) -> None:
    carpeta = tmp_path / "no_existe"
    assert listar_casos(carpeta) == [] and not carpeta.exists()


@pytest.mark.parametrize("nombre", RECHAZADAS)
def test_unc_absolutas_puntos_y_carpetas_se_rechazan_sin_tocar_el_disco(
    tmp_path: Path, nombre: str
) -> None:
    carpeta = tmp_path / "casos"
    with pytest.raises(RutaDeCasoRechazada):
        resolver_caso(nombre, carpeta)
    assert list(tmp_path.iterdir()) == []


def test_un_nombre_con_tildes_y_espacios_queda_dentro_de_la_carpeta(tmp_path: Path) -> None:
    assert resolver_caso("Obra Ñandú 2026", tmp_path) == tmp_path.resolve() / "Obra Ñandú 2026.db"


@pytest.mark.parametrize(
    ("original", "saneado"),
    [
        ("..\\..\\evil.db", "evil.db"),
        ("C:\\Users\\x\\Mi caso.db", "Mi caso.db"),
        ("presupuesto final?.db", "presupuesto final_.db"),
        ("Oficina Ñandú", "Oficina Ñandú.db"),
        ("informe: v2.db", "informe_ v2.db"),
    ],
)
def test_sanear_deja_solo_un_nombre_seguro(original: str, saneado: str) -> None:
    assert sanear_nombre(original) == saneado


@pytest.mark.parametrize("original", ["CON.db", "nul", " .db", ".."])
def test_sanear_rechaza_nombres_vacios_o_reservados(original: str) -> None:
    with pytest.raises(RutaDeCasoRechazada):
        sanear_nombre(original)


def test_crear_un_caso_lo_deja_en_head_y_no_lo_repite(tmp_path: Path) -> None:
    resultado = crear_caso("Obra nueva", tmp_path / "casos")
    assert resultado.nueva and resultado.ruta.name == "Obra nueva.db"
    assert leer_estado(resultado.ruta).revision == revision_head(Destino.CASO)
    with pytest.raises(RutaDeCasoRechazada, match="Ya existe"):
        crear_caso("Obra nueva", tmp_path / "casos")


def test_crear_con_una_ruta_se_rechaza_sin_crear_nada(tmp_path: Path) -> None:
    with pytest.raises(RutaDeCasoRechazada):
        crear_caso("..\\fuera", tmp_path / "casos")
    assert list(tmp_path.iterdir()) == []


def test_subir_un_caso_lo_copia_con_nombre_saneado_y_lo_migra(tmp_path: Path) -> None:
    contenido = (bases_prueba.carpeta_version("0.5.0") / "demo.db").read_bytes()
    resultado = subir_caso("C:\\Descargas\\Caso de Ana?.db", contenido, tmp_path / "casos")
    assert resultado.ruta.name == "Caso de Ana_.db" and resultado.juego is not None
    assert leer_estado(resultado.ruta).revision == revision_head(Destino.CASO)


def test_subir_algo_que_no_es_sqlite_no_deja_archivo(tmp_path: Path) -> None:
    with pytest.raises(BaseIlegible):
        subir_caso("notas.db", b"hola", tmp_path / "casos")
    assert not (tmp_path / "casos" / "notas.db").exists()


def test_subir_una_base_mas_nueva_no_la_deja_en_la_carpeta(tmp_path: Path) -> None:
    futura = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    with pytest.raises(BaseMasNueva):
        subir_caso("futura.db", futura.read_bytes(), tmp_path / "casos")
    assert not (tmp_path / "casos" / "futura.db").exists()
