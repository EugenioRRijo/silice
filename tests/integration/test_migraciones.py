"""Alembic en dos destinos: revisión base exacta de la 0.5.0, deriva cero (RNF-20) y vuelta atrás
de cada revisión (RF-96; spec S5 §6.1, §6.2 y §12; DA-S5-6)."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import Session

from adapters.espacio import crear_esquema_espacio
from core import models
from core.catalog import crear_esquema, crear_motor
from migraciones.comun import BaseNoAdoptable, instantanea_esquema, metadata_unida
from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION
from operacion.base_datos import (
    CARPETA_MIGRACIONES,
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    revision_head,
    revisiones_en_orden,
)
from scripts.congelar_esquema import leer_esquema
from tests.fixtures import bases_prueba

REVISION_BASE = "caso_0001_base_0_5_0"
RAIZ = Path(__file__).resolve().parents[2]
METADATAS = {Destino.CASO: METADATAS_CASO, Destino.INSTALACION: METADATAS_INSTALACION}
#: Paquetes donde puede vivir una `MetaData` con tablas (spec S5 §4.3, RNF-20).
PAQUETES_CON_TABLAS = ("core", "adapters", "ui", "seguridad", "paquete", "asistente", "produccion")


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(_url(ruta))
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def _ddl(ruta: Path) -> dict[str, str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return dict(
            conexion.execute(
                "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL "
                "AND name NOT LIKE 'sqlite_%' AND tbl_name <> 'alembic_version'"
            )
        )


def _create_all(ruta: Path, destino: Destino) -> Path:
    motor = create_engine(_url(ruta))
    try:
        for metadata in METADATAS[destino]:
            metadata.create_all(motor)
    finally:
        motor.dispose()
    return ruta


def _revision_base():
    archivo = CARPETA_MIGRACIONES / "caso" / "versions" / f"{REVISION_BASE}.py"
    especificacion = importlib.util.spec_from_file_location(REVISION_BASE, archivo)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


# --- la revisión base es el esquema EXACTO de la 0.5.0 (RV-3) ------------------------------------


def test_la_revision_base_es_el_ddl_literal_de_las_bases_de_v0_5_0() -> None:
    congeladas = {t.nombre: (t.ddl, t.indices) for t in _revision_base().TABLAS}
    assert len(congeladas) == 33  # 25 tablas de core/models + 8 esp_* (spec S5 §6.1)
    for nombre in bases_prueba.nombres("0.5.0"):
        base = bases_prueba.carpeta_version("0.5.0") / nombre
        for tabla, ddl, indices in leer_esquema(base):
            assert congeladas[tabla] == (ddl, indices), f"{nombre}: {tabla}"


def test_subir_hasta_la_revision_base_da_el_esquema_de_la_0_5_0(tmp_path: Path) -> None:
    base = tmp_path / "vacia.db"
    aplicar_revisiones(base, Destino.CASO, REVISION_BASE)
    referencia = bases_prueba.copiar_base("0.5.0", "of001.db", tmp_path / "of001.db")
    assert _ddl(base) == _ddl(referencia)
    assert _instantanea(base) == _instantanea(referencia)


def test_la_revision_base_crea_solo_lo_que_falta_y_conserva_las_filas(tmp_path: Path) -> None:
    base = tmp_path / "solo_nucleo.db"
    motor = create_engine(_url(base))
    try:
        models.Base.metadata.create_all(motor)
        with Session(motor) as sesion:
            sesion.add(models.Proyecto(nombre="P", descripcion="", dominio="civil"))
            sesion.commit()
    finally:
        motor.dispose()
    aplicar_revisiones(base, Destino.CASO)
    assert _instantanea(base) == _instantanea(_create_all(tmp_path / "todo.db", Destino.CASO))
    with closing(sqlite3.connect(base)) as conexion:
        assert conexion.execute("SELECT nombre FROM proyecto").fetchall() == [("P",)]


@pytest.mark.parametrize(
    ("sentencia", "mensaje"),
    [
        (
            "ALTER TABLE composicion_apu DROP COLUMN modalidad",
            "composicion_apu: falta la columna modalidad",
        ),
        ("ALTER TABLE partida ADD COLUMN extra TEXT", "partida: sobra la columna extra"),
    ],
)
def test_una_tabla_con_otra_forma_es_base_no_adoptable(
    tmp_path: Path, sentencia: str, mensaje: str
) -> None:
    base = _create_all(tmp_path / "alterada.db", Destino.CASO)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(
            "DROP TABLE esp_origenes"
        )  # una que falta: no debe crearse si hay diferencias
        conexion.execute(sentencia)
        conexion.commit()
    tablas_antes = set(_ddl(base))
    with pytest.raises(BaseNoAdoptable, match=re.escape(mensaje)):
        aplicar_revisiones(base, Destino.CASO)
    assert set(_ddl(base)) == tablas_antes


# --- RNF-20: deriva cero en cada destino ---------------------------------------------------------


@pytest.mark.parametrize("destino", list(Destino))
def test_head_en_vacio_es_igual_a_create_all(tmp_path: Path, destino: Destino) -> None:
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, destino)
    creada = _create_all(tmp_path / "creada.db", destino)
    assert _instantanea(migrada) == _instantanea(creada)


@pytest.mark.parametrize("destino", list(Destino))
def test_la_autogeneracion_contra_head_no_propone_cambios(tmp_path: Path, destino: Destino) -> None:
    base = tmp_path / "head.db"
    aplicar_revisiones(base, destino)
    motor = create_engine(_url(base))
    try:
        with motor.connect() as conexion:
            contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
            diferencias = compare_metadata(contexto, metadata_unida(METADATAS[destino]))
    finally:
        motor.dispose()
    assert diferencias == []


def test_crear_esquema_sobre_head_no_emite_ddl(tmp_path: Path) -> None:
    base = tmp_path / "head.db"
    aplicar_revisiones(base, Destino.CASO)
    antes = _instantanea(base)
    sentencias: list[str] = []
    motor = crear_motor(_url(base))

    def anotar(_conexion, _cursor, sentencia, *_resto) -> None:
        sentencias.append(sentencia)

    event.listen(motor, "before_cursor_execute", anotar)
    try:
        crear_esquema(motor)
        crear_esquema_espacio(motor)
    finally:
        motor.dispose()
    ddl = [
        s for s in sentencias if s.lstrip().split(" ", 1)[0].upper() in {"CREATE", "ALTER", "DROP"}
    ]
    assert sentencias and ddl == []
    assert _instantanea(base) == antes


def _declara_tablas(nodo: ast.AST) -> bool:
    if isinstance(nodo, ast.Call):
        funcion = nodo.func
        return (isinstance(funcion, ast.Name) and funcion.id == "MetaData") or (
            isinstance(funcion, ast.Attribute) and funcion.attr == "MetaData"
        )
    if isinstance(nodo, ast.ClassDef):
        return any(
            (isinstance(b, ast.Name) and b.id == "DeclarativeBase")
            or (isinstance(b, ast.Attribute) and b.attr == "DeclarativeBase")
            for b in nodo.bases
        )
    return False


def _modulos_que_declaran_tablas() -> list[str]:
    modulos = []
    for paquete in PAQUETES_CON_TABLAS:
        carpeta = RAIZ / paquete
        if not carpeta.is_dir():
            continue
        for archivo in sorted(carpeta.rglob("*.py")):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            if any(_declara_tablas(nodo) for nodo in ast.walk(arbol)):
                partes = archivo.relative_to(RAIZ).with_suffix("").parts
                modulos.append(".".join(partes[:-1] if partes[-1] == "__init__" else partes))
    return modulos


def test_toda_metadata_con_tablas_esta_en_la_lista_de_su_destino() -> None:
    registradas = [*METADATAS_CASO, *METADATAS_INSTALACION]
    modulos = _modulos_que_declaran_tablas()
    assert {"core.models.base", "adapters.espacio.persistencia"} <= set(modulos), modulos
    sueltas = []
    for nombre in modulos:
        for valor in vars(importlib.import_module(nombre)).values():
            if isinstance(valor, MetaData):
                metadata = valor
            elif isinstance(valor, type):
                metadata = getattr(valor, "metadata", None)
            else:
                continue
            if isinstance(metadata, MetaData) and metadata.tables:
                if not any(metadata is registrada for registrada in registradas):
                    sueltas.append(f"{nombre}: {sorted(metadata.tables)}")
    assert sueltas == []


# --- cada revisión baja y vuelve a subir (DA-S5-6) -----------------------------------------------


@pytest.mark.parametrize("destino", list(Destino))
def test_cada_revision_baja_y_vuelve_a_subir(tmp_path: Path, destino: Destino) -> None:
    base = tmp_path / "ida_y_vuelta.db"
    for revision in revisiones_en_orden(destino):
        aplicar_revisiones(base, destino, revision)
        arriba = _instantanea(base)
        deshacer_revisiones(base, destino, "-1")
        aplicar_revisiones(base, destino, revision)
        assert _instantanea(base) == arriba, revision
    aplicar_revisiones(base, destino)
    deshacer_revisiones(base, destino, "base")
    assert _instantanea(base) == {}


def test_la_instalacion_nace_con_las_tablas_de_seguridad_y_su_alembic_version(
    tmp_path: Path,
) -> None:
    """S3-1 llena el destino de la instalación (hasta la 0.7.0 nacía vacío)."""
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    assert revision_head(Destino.INSTALACION) == "ins_0002_produccion"
    with closing(sqlite3.connect(base)) as conexion:
        tablas = {
            n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert tablas == {
            "alembic_version", "usuario", "intento_acceso", "sesion", "evento_acceso",
            "codigo_instalacion", "empresa_propia", "clave_empresa", "empresa_registrada",
            "clave_api", "prod_material", "prod_movimiento", "prod_pesaje_sospechoso",
        }
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            ("ins_0002_produccion",)]
