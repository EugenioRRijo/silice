"""`operacion/primer_arranque.py`: emitir el código al arrancar y devolver el acceso (BCP-1; B1, B10,
B23 del diseño §10.2).

Oráculos a mano: el archivo del código es `XXXX-XXXX-XXXX-XXXX-XXXX` + salto de línea (24 + 1
caracteres), con solo el alfabeto base32; la base guarda una fila por código y exactamente una
vigente; el modo es `producto` si el instalador dejó `manifiesto.json` junto a `codigo/`.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from operacion import __main__ as cli
from operacion import config, primer_arranque
from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from seguridad import cuentas
from seguridad.modelo import CodigoInstalacion, EventoAcceso
from tests.fixtures.instalacion import AHORA, administrador, instalacion

FORMATO = re.compile(r"^(?:[A-Z2-7]{4}-){4}[A-Z2-7]{4}\n$")


def _filas(sesion) -> int:
    return sesion.scalar(select(func.count()).select_from(CodigoInstalacion))


def _vigentes(sesion) -> int:
    return sesion.scalar(
        select(func.count()).select_from(CodigoInstalacion).where(CodigoInstalacion.usado.is_(None))
    )


def test_asegurar_codigo_en_una_base_vacia_emite_y_escribe_el_archivo(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
        archivo = tmp_path / "codigo_instalacion.txt"
        assert FORMATO.fullmatch(archivo.read_text(encoding="ascii"))
        assert _filas(sesion) == 1 and _vigentes(sesion) == 1


def test_asegurar_codigo_es_idempotente(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
        escrito = (tmp_path / "codigo_instalacion.txt").read_bytes()
        for minutos in (1, 2, 60):
            cuando = AHORA + timedelta(minutes=minutos)
            assert primer_arranque.asegurar_codigo(sesion, tmp_path, cuando) is False
        assert (tmp_path / "codigo_instalacion.txt").read_bytes() == escrito
        assert _filas(sesion) == 1 and _vigentes(sesion) == 1


def test_asegurar_codigo_con_cuentas_no_emite_nada(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        antes = _filas(sesion)
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is False
        assert _filas(sesion) == antes
        assert not (tmp_path / "codigo_instalacion.txt").exists()


def test_asegurar_codigo_reemite_si_se_borro_el_archivo_e_invalida_el_anterior(
    tmp_path: Path,
) -> None:
    with instalacion(tmp_path) as sesion:
        primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA)
        viejo = (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii")
        (tmp_path / "codigo_instalacion.txt").unlink()
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA + timedelta(hours=1))
        nuevo = (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii")
        assert FORMATO.fullmatch(nuevo) and nuevo != viejo
        assert _filas(sesion) == 2 and _vigentes(sesion) == 1  # solo el último sirve


def test_asegurar_codigo_con_un_archivo_ajeno_no_lo_toca(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        (tmp_path / "codigo_instalacion.txt").write_text("K7QF-M9XR-A2PT-W4HN-C8DV\n")
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is False
        assert (tmp_path / "codigo_instalacion.txt").read_text() == "K7QF-M9XR-A2PT-W4HN-C8DV\n"


def test_el_estado_dice_solo_tres_cosas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with instalacion(tmp_path) as sesion:
        monkeypatch.setattr(config, "es_producto", lambda raiz=None: False)
        vacio = primer_arranque.estado(sesion, tmp_path)
        assert (vacio.sin_cuentas, vacio.archivo_presente, vacio.modo) == (True, False, "desarrollo")
        primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA)
        con_archivo = primer_arranque.estado(sesion, tmp_path)
        assert (con_archivo.sin_cuentas, con_archivo.archivo_presente) == (True, True)
        monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
        assert primer_arranque.estado(sesion, tmp_path).modo == "producto"
        administrador(sesion, tmp_path)  # el reclamo borra el archivo
        reclamado = primer_arranque.estado(sesion, tmp_path)
        assert (reclamado.sin_cuentas, reclamado.archivo_presente) == (False, False)
        assert set(asdict(vacio)) == {"sin_cuentas", "archivo_presente", "modo"}


def test_emitir_restablecimiento_devuelve_el_codigo_y_el_archivo(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        codigo, archivo = primer_arranque.emitir_restablecimiento(sesion, tmp_path, AHORA)
        assert archivo == tmp_path / "codigo_instalacion.txt"
        assert FORMATO.fullmatch(archivo.read_text(encoding="ascii"))
        assert archivo.read_text(encoding="ascii").replace("-", "").strip() == codigo
        fila = sesion.scalars(
            select(CodigoInstalacion).where(CodigoInstalacion.motivo == "restablecimiento")
        ).one()
        assert fila.usado is None and fila.creado == AHORA


# --- sobre la instalación de la carpeta de datos ---------------------------------------------------


@pytest.fixture
def datos():
    """La carpeta de datos temporal de `tests/conftest.py`, con los motores cerrados al salir."""
    carpeta = config.carpeta_datos()
    yield carpeta
    cerrar_motores()


def test_asegurar_codigo_de_la_instalacion_abre_la_base_de_la_carpeta_de_datos(datos) -> None:
    assert primer_arranque.asegurar_codigo_de_la_instalacion(None, AHORA) is True
    assert FORMATO.fullmatch((datos / "codigo_instalacion.txt").read_text(encoding="ascii"))
    assert primer_arranque.asegurar_codigo_de_la_instalacion(None, AHORA) is False


def test_restablecer_administrador_cierra_los_motores_y_devuelve_el_archivo(datos) -> None:
    with sesion_de_instalacion() as sesion:
        administrador(sesion, datos)
    codigo, archivo = primer_arranque.restablecer_administrador(None, AHORA)
    assert archivo == datos / "codigo_instalacion.txt" and len(codigo) == 20
    with sesion_de_instalacion() as sesion:
        eventos = sesion.scalars(
            select(EventoAcceso.detalle).where(EventoAcceso.tipo == "codigo de instalacion")
        ).all()
        assert any(d.startswith("restablecimiento") for d in eventos)


def test_la_orden_restablecer_administrador_imprime_el_codigo_y_el_plazo(datos, capsys) -> None:
    with sesion_de_instalacion() as sesion:
        administrador(sesion, datos)
    assert cli.main(["restablecer-administrador"]) == 0
    salida = capsys.readouterr().out
    escrito = (datos / "codigo_instalacion.txt").read_text(encoding="ascii").strip()
    assert FORMATO.fullmatch(escrito + "\n")
    assert escrito in salida  # el código va a la consola, que es de quien corre la orden
    assert "24 horas" in salida
    assert str(datos / "codigo_instalacion.txt") in salida
    cerrar_motores()


def test_la_orden_no_deja_el_codigo_en_un_evento(datos, capsys) -> None:
    with sesion_de_instalacion() as sesion:
        administrador(sesion, datos)
    cli.main(["restablecer-administrador"])
    codigo = (datos / "codigo_instalacion.txt").read_text(encoding="ascii").replace("-", "").strip()
    with sesion_de_instalacion() as sesion:
        for evento in sesion.scalars(select(EventoAcceso)):
            assert codigo not in f"{evento.login_intentado}{evento.detalle}"
        assert cuentas.hay_usuarios(sesion)
    cerrar_motores()
