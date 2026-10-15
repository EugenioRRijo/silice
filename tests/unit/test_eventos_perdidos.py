"""Revisión obligatoria de los eventos de seguridad perdidos al restaurar (SEG-12; spec S5 §6.5).

El conjunto esperado de diferencias se deduce a mano de las dos instalaciones sembradas en
`tests/fixtures/eventos_seguridad.py` (cada fila de `ACTUAL` contra su par de `COPIA`).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from operacion import config, eventos_perdidos
from tests.fixtures.eventos_seguridad import ACTUAL, COPIA
from tests.fixtures.eventos_seguridad import base as _base


def test_el_conjunto_exacto_de_diferencias_sembradas(tmp_path: Path) -> None:
    actual, copia = _base(tmp_path / "actual.db", ACTUAL), _base(tmp_path / "copia.db", COPIA)
    hallado = [
        (d["tipo"], d["tabla"], d["id"]) for d in eventos_perdidos.diferencias(actual, copia)
    ]
    assert len(hallado) == len(set(hallado))  # ninguna repetida
    assert set(hallado) == {
        ("cuenta_reactivada", "usuario", 1),
        ("roles_distintos", "usuario", 2),
        ("registro_posterior_perdido", "usuario", 3),
        ("clave_revivida", "clave_empresa", 1),
        ("clave_revivida", "empresa_registrada", 1),
        ("clave_api_revivida", "clave_api", 1),
        ("registro_posterior_perdido", "clave_api", 2),
    }


def test_cada_diferencia_dice_el_estado_actual_y_el_que_volveria(tmp_path: Path) -> None:
    actual, copia = _base(tmp_path / "actual.db", ACTUAL), _base(tmp_path / "copia.db", COPIA)
    por_clave = {
        (d["tipo"], d["tabla"], d["id"]): d for d in eventos_perdidos.diferencias(actual, copia)
    }
    assert por_clave[("cuenta_reactivada", "usuario", 1)] == {
        "tipo": "cuenta_reactivada",
        "tabla": "usuario",
        "id": 1,
        "etiqueta": "ana",
        "actual": {"activo": 0, "roles": "arma"},
        "al_restaurar": {"activo": 1, "roles": "arma"},
    }
    nuevo = por_clave[("registro_posterior_perdido", "clave_api", 2)]
    assert nuevo["etiqueta"] == "nuevo" and nuevo["al_restaurar"] is None


def test_las_diferencias_no_llevan_secretos(tmp_path: Path) -> None:
    actual, copia = _base(tmp_path / "actual.db", ACTUAL), _base(tmp_path / "copia.db", COPIA)
    texto = json.dumps(eventos_perdidos.diferencias(actual, copia), ensure_ascii=False)
    for secreto in ("ARGON-", "SHA-", "cifrada"):
        assert secreto not in texto
    assert "ana" in texto and "AAAA" in texto  # lo que identifica, sí


def test_sin_diferencias_no_hay_nada_que_revisar(tmp_path: Path) -> None:
    uno, otro = _base(tmp_path / "a.db", COPIA), _base(tmp_path / "b.db", COPIA)
    assert eventos_perdidos.diferencias(uno, otro) == []


def test_lo_que_la_restauracion_endurece_no_es_una_diferencia(tmp_path: Path) -> None:
    """Al revés: la copia tiene la cuenta desactivada y la clave revocada. Restaurarla no revive
    nada (solo pierde una reactivación y una clave activa): no hay nada que revisar."""
    actual = _base(
        tmp_path / "actual.db",
        {
            "usuario": [(1, "ana", 1, "arma", "X")],
            "clave_empresa": [(1, "AAAA", "activa", None)],
            "clave_api": [(1, "plugin", 0, "S")],
        },
    )
    copia = _base(
        tmp_path / "copia.db",
        {
            "usuario": [(1, "ana", 0, "arma", "X")],
            "clave_empresa": [(1, "AAAA", "retirada", None)],
            "clave_api": [(1, "plugin", 1, "S")],
        },
    )
    assert eventos_perdidos.diferencias(actual, copia) == []


@pytest.mark.parametrize("estado", ["retirada", "revocada"])
def test_una_clave_retirada_o_revocada_que_vuelve_activa_se_lista(
    tmp_path: Path, estado: str
) -> None:
    actual = _base(tmp_path / "a.db", {"clave_empresa": [(1, "AAAA", estado, None)]})
    copia = _base(tmp_path / "c.db", {"clave_empresa": [(1, "AAAA", "activa", b"k")]})
    tipos = [d["tipo"] for d in eventos_perdidos.diferencias(actual, copia)]
    assert tipos == ["clave_revivida"]


def test_una_instalacion_sin_esas_tablas_no_falla(tmp_path: Path) -> None:
    vacia = tmp_path / "vacia.db"
    sqlite3.connect(vacia).close()
    con_datos = _base(tmp_path / "c.db", COPIA)
    assert eventos_perdidos.diferencias(vacia, con_datos) == []
    assert eventos_perdidos.diferencias(con_datos, vacia) == []
    assert eventos_perdidos.diferencias(tmp_path / "no_existe.db", con_datos) == []


def test_comparar_no_modifica_ninguna_de_las_dos_bases(tmp_path: Path) -> None:
    actual, copia = _base(tmp_path / "actual.db", ACTUAL), _base(tmp_path / "copia.db", COPIA)
    antes = (actual.read_bytes(), copia.read_bytes())
    eventos_perdidos.diferencias(actual, copia)
    assert (actual.read_bytes(), copia.read_bytes()) == antes


def test_las_tablas_vigiladas_existen_en_el_modelo_de_s3() -> None:
    from seguridad.modelo import Base

    for tabla, regla in eventos_perdidos.TABLAS_VIGILADAS.items():
        columnas = {c.name for c in Base.metadata.tables[tabla].columns}
        assert {regla.clave, regla.etiqueta, *regla.estado} <= columnas, tabla


def _pendiente(nombre: str, contenido: str) -> Path:
    ruta = config.carpeta_datos() / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_sin_carpeta_de_datos_no_hay_pendientes() -> None:
    assert not config.carpeta_datos().exists() or eventos_perdidos.pendientes() == []
    assert eventos_perdidos.pendientes({config.VARIABLE_DATOS: "/no/existe/silice"}) == []


def test_un_archivo_sin_revisar_bloquea_las_operaciones_sensibles() -> None:
    assert eventos_perdidos.bloqueadas() is False
    archivo = _pendiente(
        "eventos_perdidos_20261011-100000.json", '{"revisado": false, "eventos": []}'
    )
    assert eventos_perdidos.pendientes() == [archivo] and eventos_perdidos.bloqueadas() is True
    eventos_perdidos.marcar_revisado(archivo, por="ana")
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert datos["revisado"] is True and datos["revisado_por"] == "ana" and datos["revisado_en"]
    assert datos["eventos"] == []  # lo demás se conserva
    assert eventos_perdidos.bloqueadas() is False
    assert [p.name for p in archivo.parent.iterdir()] == [archivo.name]  # sin .tmp


@pytest.mark.parametrize(
    "contenido",
    ["{no es json", "[]", '{"eventos": []}', "", '{"revisado": "true"}', '{"revisado": 1}'],
)
def test_un_archivo_ilegible_o_sin_marca_cuenta_como_pendiente(contenido: str) -> None:
    _pendiente("eventos_perdidos_20261011-110000.json", contenido)
    assert eventos_perdidos.bloqueadas() is True


def test_otros_json_de_la_carpeta_no_cuentan() -> None:
    _pendiente("ficha.json", '{"revisado": false}')
    _pendiente("eventos_perdidos.txt", '{"revisado": false}')
    assert eventos_perdidos.bloqueadas() is False


def test_dos_pendientes_hay_que_revisar_los_dos() -> None:
    uno = _pendiente("eventos_perdidos_20261011-100000.json", '{"revisado": false}')
    otro = _pendiente("eventos_perdidos_20261012-100000.json", '{"revisado": false}')
    assert eventos_perdidos.pendientes() == [uno, otro]
    eventos_perdidos.marcar_revisado(uno)
    assert eventos_perdidos.pendientes() == [otro] and eventos_perdidos.bloqueadas() is True
    eventos_perdidos.marcar_revisado(otro)
    assert eventos_perdidos.bloqueadas() is False


def test_marcar_revisado_un_archivo_ilegible_lo_deja_revisado() -> None:
    archivo = _pendiente("eventos_perdidos_20261011-140000.json", "{no es json")
    eventos_perdidos.marcar_revisado(archivo, por="admin")
    assert eventos_perdidos.bloqueadas() is False


def test_el_resumen_cuenta_eventos_y_diferencias() -> None:
    archivo = _pendiente(
        "eventos_perdidos_20261011-120000.json",
        json.dumps({"revisado": False, "eventos": [{"id": 2}], "diferencias": [{"tipo": "x"}]}),
    )
    assert eventos_perdidos.resumen(archivo) == {
        "archivo": archivo.name,
        "revisado": False,
        "eventos": 1,
        "diferencias": 1,
        "juego": None,
    }


def test_el_resumen_de_un_archivo_ilegible_no_falla() -> None:
    archivo = _pendiente("eventos_perdidos_20261011-150000.json", "[]")
    assert eventos_perdidos.resumen(archivo) == {
        "archivo": archivo.name,
        "revisado": False,
        "eventos": 0,
        "diferencias": 0,
        "juego": None,
    }


def test_la_base_de_la_fixture_es_legible_solo_con_las_columnas_justas(tmp_path: Path) -> None:
    """Guardia de la propia fixture: la huella de la contraseña está en la base, de modo que la
    prueba de «sin secretos» compara contra algo que sí existía."""
    ruta = _base(tmp_path / "x.db", ACTUAL)
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT huella_clave FROM usuario WHERE id = 1").fetchone() == (
            "ARGON-A",
        )
