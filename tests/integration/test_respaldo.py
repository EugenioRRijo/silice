"""Juegos de respaldo de las dos bases, en una ficha, y su restauración (RF-96 b y f; spec S5 §6.3
y §6.5). En la 0.6.0 la base de la instalación no tiene tablas: el juego ya la lleva y la lista de
eventos perdidos ya la lee."""

from __future__ import annotations

import json
import sqlite3
import tomllib
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from operacion import config, respaldo
from operacion.base_datos import Destino, aplicar_revisiones, revision_head, revisiones_conocidas
from tests.fixtures import bases_prueba


@dataclass(frozen=True)
class Datos:
    carpeta: Path
    casos: Path
    instalacion: Path
    respaldos: Path


@pytest.fixture
def datos(tmp_path: Path) -> Datos:
    carpeta = tmp_path / "datos"
    return Datos(carpeta, carpeta / "casos", carpeta / "instalacion.db", carpeta / "respaldos")


def _heads() -> dict[str, str | None]:
    return {d.value: revision_head(d) for d in Destino}


def _respaldar(datos: Datos, casos: list[Path], motivo: str = "migracion", ahora=None) -> Path:
    return respaldo.respaldar(
        casos,
        motivo,
        ruta_instalacion=datos.instalacion,
        carpeta_respaldos=datos.respaldos,
        heads=_heads(),
        ahora=ahora,
    )


def _restaurar(datos: Datos, juego: Path, solo_caso: str | None = None) -> respaldo.Restauracion:
    return respaldo.restaurar(
        juego,
        ruta_instalacion=datos.instalacion,
        carpeta_casos=datos.casos,
        carpeta_datos=datos.carpeta,
        carpeta_respaldos=datos.respaldos,
        heads=_heads(),
        conocidas={d.value: revisiones_conocidas(d) for d in Destino},
        solo_caso=solo_caso,
    )


def _instalacion_vacia(datos: Datos) -> None:
    datos.carpeta.mkdir(parents=True, exist_ok=True)
    aplicar_revisiones(datos.instalacion, Destino.INSTALACION)


def _filas(ruta: Path) -> dict[str, int]:
    with closing(respaldo.abrir_solo_lectura(ruta)) as conexion:
        return respaldo.filas_por_tabla(conexion)


def test_el_juego_trae_la_copia_verificada_y_su_ficha(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    ficha = respaldo.leer_ficha(juego)
    with (config.RAIZ / "pyproject.toml").open("rb") as archivo:
        assert ficha["version_silice"] == tomllib.load(archivo)["project"]["version"]
    assert ficha["motivo"] == "migracion" and ficha["ultimo_evento_acceso"] is None
    [base] = ficha["bases"]
    assert (base["archivo"], base["destino"]) == ("casos/demo.db", "caso")
    assert base["revision_origen"] is None
    assert base["revision_destino"] == revision_head(Destino.CASO)
    assert base["sha256"] == respaldo.huella(juego / "casos" / "demo.db")
    assert (
        base["filas_por_tabla"]
        == bases_prueba.ficha("0.5.0")["bases"]["demo.db"]["filas_por_tabla"]
    )
    respaldo.verificar_integridad(juego / "casos" / "demo.db")
    assert not (juego / "instalacion.db").exists()


def test_la_instalacion_va_siempre_en_el_juego_aunque_no_se_migre(datos: Datos) -> None:
    _instalacion_vacia(datos)  # desde S3-1: en `head`, con las tablas de seguridad sin filas
    juego = _respaldar(datos, [])
    [base] = respaldo.leer_ficha(juego)["bases"]
    assert (base["archivo"], base["destino"], base["revision_origen"]) == (
        "instalacion.db",
        "instalacion",
        "ins_0002_produccion",
    )
    assert base["filas_por_tabla"] == {
        "alembic_version": 1, "usuario": 0, "intento_acceso": 0, "sesion": 0,
        "evento_acceso": 0, "codigo_instalacion": 0, "empresa_propia": 0, "clave_empresa": 0,
        "empresa_registrada": 0, "clave_api": 0, "prod_material": 0, "prod_movimiento": 0,
        "prod_pesaje_sospechoso": 0,
    }


def test_se_respalda_con_la_base_abierta_y_una_escritura_sin_confirmar(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    antes = _filas(caso)
    otro = sqlite3.connect(caso, isolation_level=None)
    try:
        otro.execute("BEGIN IMMEDIATE")
        otro.execute(
            "INSERT INTO proyecto (nombre, descripcion, dominio) "
            "VALUES ('sin confirmar', '', 'civil')"
        )
        juego = _respaldar(datos, [caso])
    finally:
        otro.execute("ROLLBACK")
        otro.close()
    assert _filas(juego / "casos" / "demo.db") == antes


def test_disco_lleno_no_deja_juego_ni_toca_la_base(datos: Datos, monkeypatch) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    antes = respaldo.huella(caso)

    def disco_lleno(_origen: Path, _destino: Path) -> None:
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(respaldo, "copiar_sqlite", disco_lleno)
    with pytest.raises(respaldo.RespaldoFallido, match="disk is full"):
        _respaldar(datos, [caso])
    assert list(datos.respaldos.iterdir()) == []
    assert respaldo.huella(caso) == antes


def test_una_copia_ilegible_no_deja_juego(datos: Datos, monkeypatch) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")

    def copia_rota(_origen: Path, destino: Path) -> None:
        destino.write_bytes(b"esto no es una base de datos" * 200)

    monkeypatch.setattr(respaldo, "copiar_sqlite", copia_rota)
    with pytest.raises(respaldo.RespaldoFallido, match="no es una base legible"):
        _respaldar(datos, [caso])
    assert list(datos.respaldos.iterdir()) == []


def test_juego_en_una_ruta_de_onedrive_con_espacios_y_acentos(tmp_path: Path) -> None:
    carpeta = tmp_path / "OneDrive - Personal" / "Escritorio" / "TÉSIS ñ" / "datos"
    datos = Datos(carpeta, carpeta / "casos", carpeta / "instalacion.db", carpeta / "respaldos")
    caso = bases_prueba.copiar_base(
        "0.5.0", "of001.db", datos.casos / "Oficina Ñandú con espacios.db"
    )
    juego = _respaldar(datos, [caso])
    [base] = respaldo.leer_ficha(juego)["bases"]
    assert base["archivo"] == "casos/Oficina Ñandú con espacios.db"
    respaldo.verificar_integridad(juego / base["archivo"])


def test_se_conservan_los_cinco_ultimos_de_migracion_y_todos_los_manuales(datos: Datos) -> None:
    inicio = datetime(2026, 10, 11, 8, 0, 0)
    de_migracion = [_respaldar(datos, [], ahora=inicio + timedelta(minutes=n)) for n in range(7)]
    manual = _respaldar(datos, [], motivo="manual", ahora=inicio - timedelta(days=1))
    borrados = respaldo.podar_juegos(datos.respaldos)
    assert borrados == de_migracion[:2]
    quedan = [c for c, _ in respaldo.listar_juegos(datos.respaldos)]
    assert quedan == [manual, *de_migracion[2:]]


def test_restaurar_devuelve_el_caso_y_guarda_antes_las_bases_actuales(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    with closing(sqlite3.connect(caso)) as conexion:
        conexion.execute(
            "INSERT INTO proyecto (nombre, descripcion, dominio) VALUES ('despues', '', 'civil')"
        )
        conexion.commit()
    modificadas = _filas(caso)
    resultado = _restaurar(datos, juego)
    assert resultado.restauradas == (datos.casos / "demo.db",)
    assert resultado.eventos_perdidos is None
    assert _filas(caso) == _filas(juego / "casos" / "demo.db")
    assert respaldo.leer_ficha(resultado.antes)["motivo"] == "antes_de_restaurar"
    assert _filas(resultado.antes / "casos" / "demo.db") == modificadas


def test_restaurar_un_juego_con_la_instalacion_vacia_de_la_0_6_0(datos: Datos) -> None:
    _instalacion_vacia(datos)
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    resultado = _restaurar(datos, juego)
    assert sorted(r.name for r in resultado.restauradas) == ["demo.db", "instalacion.db"]
    perdidos = json.loads(resultado.eventos_perdidos.read_text(encoding="utf-8"))
    assert perdidos["revisado"] is False and perdidos["eventos"] == []
    assert resultado.eventos_perdidos.parent == datos.carpeta


def test_restaurar_la_instalacion_lista_los_eventos_posteriores_al_juego(datos: Datos) -> None:
    datos.carpeta.mkdir(parents=True)
    with closing(sqlite3.connect(datos.instalacion)) as conexion:
        # Las columnas que lee la lista son las de `evento_acceso` de S3 §12 (id, fecha_hora).
        conexion.execute(
            "CREATE TABLE evento_acceso "
            "(id INTEGER PRIMARY KEY, fecha_hora TEXT NOT NULL, tipo TEXT NOT NULL)"
        )
        conexion.executemany(
            "INSERT INTO evento_acceso VALUES (?, ?, ?)",
            [(1, "2026-10-01T08:00:00", "entrada"), (2, "2026-10-01T09:00:00", "revocación")],
        )
        conexion.commit()
    juego = _respaldar(datos, [])
    assert respaldo.leer_ficha(juego)["ultimo_evento_acceso"] == {
        "id": 2,
        "fecha_hora": "2026-10-01T09:00:00",
    }
    with closing(sqlite3.connect(datos.instalacion)) as conexion:
        conexion.execute("INSERT INTO evento_acceso VALUES (3, '2026-10-02T10:00:00', 'baja')")
        conexion.commit()
    resultado = _restaurar(datos, juego)
    perdidos = json.loads(resultado.eventos_perdidos.read_text(encoding="utf-8"))
    assert perdidos["eventos"] == [{"id": 3, "fecha_hora": "2026-10-02T10:00:00", "tipo": "baja"}]


def test_solo_caso_restaura_ese_caso_y_no_toca_la_instalacion(datos: Datos) -> None:
    _instalacion_vacia(datos)
    a = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "a.db")
    b = bases_prueba.copiar_base("0.5.0", "ti001.db", datos.casos / "b.db")
    juego = _respaldar(datos, [a, b])
    instalacion_antes = respaldo.huella(datos.instalacion)
    b_antes = respaldo.huella(b)
    resultado = _restaurar(datos, juego, solo_caso="a")
    assert resultado.restauradas == (datos.casos / "a.db",) and resultado.eventos_perdidos is None
    assert respaldo.huella(datos.instalacion) == instalacion_antes and respaldo.huella(b) == b_antes


def test_un_juego_alterado_no_se_restaura(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    with (juego / "casos" / "demo.db").open("ab") as copia:
        copia.write(b"\0")
    antes = respaldo.huella(caso)
    with pytest.raises(respaldo.RespaldoFallido, match="alterada"):
        _restaurar(datos, juego)
    assert respaldo.huella(caso) == antes


def test_un_juego_de_una_version_mas_nueva_no_se_restaura(datos: Datos) -> None:
    futura = bases_prueba.crear_base_futura(datos.casos / "futura.db")
    juego = _respaldar(datos, [futura])
    with pytest.raises(respaldo.RespaldoFallido, match="versión más nueva"):
        _restaurar(datos, juego)
