"""Restaurar un juego con `instalacion.db` deja el listado exacto y bloquea (RF-96 f; spec §6.5).

El juego se arma con `respaldar_todo` sobre la instalación `COPIA`; después la instalación
«sigue» (`ACTUAL`: revoca, desactiva y registra) y se restaura el juego. Lo esperado se deduce a
mano de las dos instalaciones de `tests/fixtures/eventos_seguridad.py`.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing

from operacion import base_datos, config, eventos_perdidos
from tests.fixtures.eventos_seguridad import ACTUAL, COPIA
from tests.fixtures.eventos_seguridad import base as _base


def _reemplazar(ruta, filas) -> None:
    ruta.unlink()
    _base(ruta, filas)


def test_restaurar_lista_lo_perdido_y_bloquea() -> None:
    instalacion = config.ruta_instalacion()
    instalacion.parent.mkdir(parents=True, exist_ok=True)
    _base(instalacion, COPIA)
    juego = base_datos.respaldar_todo()
    _reemplazar(instalacion, ACTUAL)  # la instalación siguió: revocó, desactivó y registró
    assert eventos_perdidos.bloqueadas() is False

    resultado = base_datos.restaurar_juego(juego)

    assert resultado.eventos_perdidos is not None
    assert resultado.eventos_perdidos.parent == config.carpeta_datos()
    assert resultado.eventos_perdidos.name.startswith("eventos_perdidos_")
    datos = json.loads(resultado.eventos_perdidos.read_text(encoding="utf-8"))
    assert datos["revisado"] is False and datos["juego"] == str(juego)
    # solo el evento 2, posterior al último que guardó el juego
    assert [(e["id"], e["tipo"]) for e in datos["eventos"]] == [(2, "revocacion")]
    assert {(d["tipo"], d["tabla"], d["id"]) for d in datos["diferencias"]} == {
        ("cuenta_reactivada", "usuario", 1),
        ("roles_distintos", "usuario", 2),
        ("registro_posterior_perdido", "usuario", 3),
        ("clave_revivida", "clave_empresa", 1),
        ("clave_revivida", "empresa_registrada", 1),
        ("clave_api_revivida", "clave_api", 1),
        ("registro_posterior_perdido", "clave_api", 2),
    }
    texto = resultado.eventos_perdidos.read_text(encoding="utf-8")
    assert "ARGON-" not in texto and "SHA-" not in texto  # ninguna huella ni secreto
    with closing(sqlite3.connect(instalacion)) as conexion:  # la base quedó como en el juego
        assert conexion.execute("SELECT COUNT(*) FROM usuario").fetchone() == (2,)
        assert conexion.execute("SELECT activo FROM usuario WHERE id = 1").fetchone() == (1,)
    assert eventos_perdidos.bloqueadas() is True
    eventos_perdidos.marcar_revisado(resultado.eventos_perdidos, por="admin")
    assert eventos_perdidos.bloqueadas() is False


def test_restaurar_sin_cambios_igual_pide_revision_pero_sin_diferencias() -> None:
    """Frontera: nada cambió después del juego. Se escribe el archivo (la regla es «restaurar la
    instalación exige revisar»), con cero eventos y cero diferencias."""
    instalacion = config.ruta_instalacion()
    instalacion.parent.mkdir(parents=True, exist_ok=True)
    _base(instalacion, COPIA)
    juego = base_datos.respaldar_todo()
    resultado = base_datos.restaurar_juego(juego)
    datos = json.loads(resultado.eventos_perdidos.read_text(encoding="utf-8"))
    assert (datos["eventos"], datos["diferencias"], datos["revisado"]) == ([], [], False)
    assert eventos_perdidos.bloqueadas() is True


def test_restaurar_solo_un_caso_no_toca_la_seguridad_ni_pide_revision() -> None:
    caso = base_datos.preparar_base(config.ruta_caso_por_defecto()).ruta
    juego = base_datos.respaldar_todo()
    resultado = base_datos.restaurar_juego(juego, solo_caso=caso.stem)
    assert resultado.eventos_perdidos is None and eventos_perdidos.bloqueadas() is False
    assert resultado.restauradas == (caso,)
