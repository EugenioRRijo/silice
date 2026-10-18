"""`preparar_base`: crear, adoptar y migrar con respaldo previo; rechazar sin tocar (RF-96 a, c, d;
spec S5 §6.3 y §6.4; RV-3). Las bases viven en `tmp_path`; los juegos, en la carpeta de datos
temporal de `tests/conftest.py`."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from operacion import base_datos, config, respaldo
from operacion.base_datos import (
    BaseBloqueada,
    BaseIlegible,
    BaseMasNueva,
    BaseNoAdoptable,
    Destino,
    MigracionFallida,
    RespaldoFallido,
    RutaDeCasoRechazada,
    leer_estado,
    migrar_todo,
    preparar_base,
    revision_head,
)
from tests.fixtures import bases_prueba

FICHA = bases_prueba.ficha("0.5.0")

REVISION_QUE_FALLA = '''"""Revisión de prueba: crea una tabla y falla a medias (RF-96 c)."""
import sqlalchemy as sa
from alembic import op

revision = "caso_9000_falla"
down_revision = "{abajo}"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tabla_a_medias", sa.Column("id", sa.Integer, primary_key=True))
    raise RuntimeError("falla inyectada")


def downgrade() -> None:
    op.drop_table("tabla_a_medias")
'''


def _juegos() -> list:
    return respaldo.listar_juegos(config.carpeta_respaldos())


def _demo(tmp_path: Path) -> Path:
    return bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")


def test_una_base_que_no_existe_nace_en_head_sin_juego(tmp_path: Path) -> None:
    ruta = tmp_path / "nueva" / "caso.db"
    resultado = preparar_base(ruta)
    assert (resultado.nueva, resultado.juego) == (True, None)
    assert resultado.revision_destino == revision_head(Destino.CASO)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert _juegos() == []


def test_un_archivo_vacio_nace_en_head(tmp_path: Path) -> None:
    ruta = tmp_path / "vacia.db"
    ruta.touch()
    assert preparar_base(ruta).nueva
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)


@pytest.mark.parametrize("nombre", bases_prueba.nombres("0.5.0"))
def test_una_base_de_la_0_5_0_se_adopta_con_juego_y_recarga_igual_que_su_ficha(
    tmp_path: Path, nombre: str
) -> None:
    ruta = bases_prueba.copiar_base("0.5.0", nombre, tmp_path / nombre)
    resultado = preparar_base(ruta)
    assert resultado.revision_origen is None and resultado.juego is not None
    [base] = [b for b in respaldo.leer_ficha(resultado.juego)["bases"] if b["destino"] == "caso"]
    assert base["revision_origen"] is None
    assert base["revision_destino"] == revision_head(Destino.CASO)
    assert base["filas_por_tabla"] == FICHA["bases"][nombre]["filas_por_tabla"]
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert bases_prueba.diferencias_con_ficha(ruta, FICHA["bases"][nombre]) == []


def test_preparar_dos_veces_no_crea_otro_juego_ni_cambia_la_base(tmp_path: Path) -> None:
    ruta = _demo(tmp_path)
    preparar_base(ruta)
    antes, juegos = respaldo.huella(ruta), len(_juegos())
    segundo = preparar_base(ruta)
    assert segundo.juego is None and not segundo.nueva
    assert respaldo.huella(ruta) == antes and len(_juegos()) == juegos


def test_un_fallo_inyectado_en_una_revision_deja_la_base_como_estaba(
    tmp_path: Path, monkeypatch
) -> None:
    versiones = tmp_path / "versiones de prueba"
    versiones.mkdir()
    (versiones / "caso_9000_falla.py").write_text(
        REVISION_QUE_FALLA.format(abajo=revision_head(Destino.CASO)), encoding="utf-8"
    )
    original = base_datos._configuracion

    def con_la_revision_que_falla(destino: Destino):
        configuracion = original(destino)
        if destino is Destino.CASO:
            propias = base_datos.CARPETA_MIGRACIONES / "caso" / "versions"
            ubicaciones = os.pathsep.join([str(propias), str(versiones)]).replace("%", "%%")
            configuracion.set_main_option("version_locations", ubicaciones)
        return configuracion

    monkeypatch.setattr(base_datos, "_configuracion", con_la_revision_que_falla)
    base_datos._guion.cache_clear()
    try:
        ruta = _demo(tmp_path)
        antes = respaldo.huella(ruta)
        with pytest.raises(MigracionFallida, match="falla inyectada"):
            preparar_base(ruta)
        assert respaldo.huella(ruta) == antes
        assert not ruta.with_name(ruta.name + base_datos.SUFIJO_TRABAJO).exists()
        assert len(_juegos()) == 1
    finally:
        base_datos._guion.cache_clear()


def test_una_base_sin_modalidad_no_es_adoptable_y_no_se_toca(tmp_path: Path) -> None:
    ruta = _demo(tmp_path)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("ALTER TABLE composicion_apu DROP COLUMN modalidad")
        conexion.commit()
    antes = respaldo.huella(ruta)
    with pytest.raises(BaseNoAdoptable, match="composicion_apu: falta la columna modalidad"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes


def test_una_base_de_una_version_mas_nueva_no_se_toca(tmp_path: Path) -> None:
    ruta = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    antes = respaldo.huella(ruta)
    with pytest.raises(BaseMasNueva, match="versión más nueva de Sílice"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes and _juegos() == []


def test_un_archivo_que_no_es_sqlite_es_ilegible_y_no_se_toca(tmp_path: Path) -> None:
    ruta = tmp_path / "notas.db"
    ruta.write_text("esto no es una base\n" * 50, encoding="utf-8")
    antes = respaldo.huella(ruta)
    with pytest.raises(BaseIlegible, match="file is not a database"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes


def test_una_base_con_una_pagina_danada_no_se_migra(tmp_path: Path) -> None:
    ruta = _demo(tmp_path)
    with closing(sqlite3.connect(ruta)) as conexion:
        tamano = conexion.execute("PRAGMA page_size").fetchone()[0]
        raiz = conexion.execute(
            "SELECT rootpage FROM sqlite_master WHERE name = 'partida'"
        ).fetchone()[0]
    datos = bytearray(ruta.read_bytes())
    inicio = (raiz - 1) * tamano
    datos[inicio : inicio + 64] = b"\xff" * 64
    ruta.write_bytes(bytes(datos))
    antes = respaldo.huella(ruta)
    with pytest.raises(RespaldoFallido):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes and _juegos() == []


def test_una_base_bloqueada_por_otro_proceso_se_rechaza_sin_tocarla(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(respaldo, "ESPERA_BLOQUEO_S", 0.2)
    ruta = _demo(tmp_path)
    antes = respaldo.huella(ruta)
    otro = sqlite3.connect(ruta, isolation_level=None)
    try:
        otro.execute("BEGIN EXCLUSIVE")
        with pytest.raises(BaseBloqueada, match="bloqueada"):
            preparar_base(ruta)
    finally:
        otro.execute("ROLLBACK")
        otro.close()
    assert respaldo.huella(ruta) == antes


def test_una_base_que_cambia_durante_la_migracion_no_se_pisa(tmp_path: Path, monkeypatch) -> None:
    ruta = _demo(tmp_path)
    original = base_datos.aplicar_revisiones

    def y_mientras_otra_ventana_escribe(
        trabajo: Path, destino: Destino, objetivo: str = "head"
    ) -> None:
        original(trabajo, destino, objetivo)
        with closing(sqlite3.connect(ruta)) as conexion:
            conexion.execute(
                "INSERT INTO proyecto (nombre, descripcion, dominio) "
                "VALUES ('escrito durante la migracion', '', 'civil')"
            )
            conexion.commit()

    monkeypatch.setattr(base_datos, "aplicar_revisiones", y_mientras_otra_ventana_escribe)
    with pytest.raises(BaseBloqueada, match="cambió mientras se migraba"):
        preparar_base(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        escritos = conexion.execute(
            "SELECT count(*) FROM proyecto WHERE nombre = 'escrito durante la migracion'"
        ).fetchone()[0]
        tablas = {n for (n,) in conexion.execute("SELECT name FROM sqlite_master")}
    assert escritos == 1 and "alembic_version" not in tablas


def test_disco_lleno_al_respaldar_no_migra_ni_toca_la_base(tmp_path: Path, monkeypatch) -> None:
    ruta = _demo(tmp_path)
    antes = respaldo.huella(ruta)

    def disco_lleno(_origen: Path, _destino: Path) -> None:
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(respaldo, "copiar_sqlite", disco_lleno)
    with pytest.raises(RespaldoFallido, match="disk is full"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes and _juegos() == []
    assert leer_estado(ruta).revision is None
    assert not ruta.with_name(ruta.name + base_datos.SUFIJO_TRABAJO).exists()


def test_adopcion_en_una_carpeta_de_onedrive_con_espacios_y_acentos(
    tmp_path: Path, monkeypatch
) -> None:
    datos = tmp_path / "OneDrive - Personal" / "Escritorio" / "TÉSIS ñ" / "datos"
    monkeypatch.setenv(config.VARIABLE_DATOS, str(datos))
    ruta = bases_prueba.copiar_base("0.5.0", "of001.db", datos / "casos" / "Oficina Ñandú.db")
    resultado = preparar_base(ruta)
    assert resultado.juego is not None and resultado.juego.is_relative_to(datos.resolve())
    assert bases_prueba.diferencias_con_ficha(ruta, FICHA["bases"]["of001.db"]) == []


def test_la_base_de_la_instalacion_nace_con_las_tablas_de_seguridad() -> None:
    """S3-1 llena el destino de la instalación (hasta la 0.7.0 nacía vacío)."""
    ruta = config.ruta_instalacion()
    primero = preparar_base(ruta, Destino.INSTALACION)
    assert primero.nueva and primero.revision_destino == "ins_0002_produccion"
    with closing(sqlite3.connect(ruta)) as conexion:
        tablas = {
            n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert tablas == {
        "alembic_version", "usuario", "intento_acceso", "sesion", "evento_acceso",
        "codigo_instalacion", "empresa_propia", "clave_empresa", "empresa_registrada",
        "clave_api", "prod_material", "prod_movimiento", "prod_pesaje_sospechoso",
    }
    segundo = preparar_base(ruta, Destino.INSTALACION)
    assert segundo.juego is None and not segundo.nueva


def test_migrar_lleva_todo_a_head_con_un_solo_juego() -> None:
    casos = config.carpeta_casos()
    bases_prueba.copiar_base("0.5.0", "demo.db", casos / "demo.db")
    bases_prueba.copiar_base("0.5.0", "ti001.db", casos / "ti001.db")
    preparar_base(casos / "silice.db")
    resultados = migrar_todo()
    [(_, ficha)] = _juegos()
    assert sorted(b["archivo"] for b in ficha["bases"]) == [
        "casos/demo.db",
        "casos/ti001.db",
        "instalacion.db",
    ]
    assert {r.ruta.name: r.juego is not None for r in resultados} == {
        "instalacion.db": False,
        "demo.db": True,
        "silice.db": False,
        "ti001.db": True,
    }
    assert all(leer_estado(r.ruta).revision == revision_head(r.destino) for r in resultados)


def test_adoptar_la_base_de_trabajo_anterior_la_copia_y_no_la_toca(tmp_path: Path) -> None:
    anterior = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "data" / "apu.db")
    antes = respaldo.huella(anterior)
    resultado = base_datos.adoptar_base(anterior, "silice")
    assert resultado.ruta == config.ruta_caso_por_defecto()
    assert respaldo.huella(anterior) == antes
    assert bases_prueba.diferencias_con_ficha(resultado.ruta, FICHA["bases"]["demo.db"]) == []
    with pytest.raises(RutaDeCasoRechazada, match="Ya existe"):
        base_datos.adoptar_base(anterior, "silice")
