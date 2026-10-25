"""`operacion/primer_arranque.py`: emitir el código al arrancar y devolver el acceso (BCP-1; B1 y
B10 del diseño §10.2).

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
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, instalacion

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


# --- el archivo rancio (un `codigo_instalacion.txt` cuyo código no está vigente en la base) ------
#
# Caso real: la `instalacion.db` se recreó (o se restauró) y el `.txt` quedó. Antes, con el archivo
# presente, `asegurar_codigo` no hacía nada: el archivo mostraba un código que la base no conoce y
# el reclamo daba 401 para siempre (y 423 al quinto intento). Ahora, sin cuentas, si el código del
# archivo no es uno vigente en la base, se emite otro y se reescribe el archivo.

RANCIO = "KAQF-MZXR-A2PT-W4HN-CEDV\n"  # forma válida, pero ninguna base de la prueba lo emitió


def _reclamar(sesion, texto: str, carpeta: Path):
    return cuentas.reclamar_instalacion(
        sesion,
        texto,
        "dueno",
        "Dueña Demo",
        CONTRASENA,
        AHORA,
        carpeta,
        freno=cuentas.FrenoGlobal(),
    )


def test_sin_cuentas_un_archivo_que_la_base_no_conoce_se_reemplaza(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        (tmp_path / "codigo_instalacion.txt").write_text(RANCIO, encoding="ascii")
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
        nuevo = (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii")
        assert FORMATO.fullmatch(nuevo) and nuevo != RANCIO
        assert _filas(sesion) == 1 and _vigentes(sesion) == 1
        assert _reclamar(sesion, nuevo, tmp_path).login == "dueno"


def test_tras_recrear_la_instalacion_el_archivo_viejo_se_reemite_y_el_nuevo_sirve(
    tmp_path: Path,
) -> None:
    with instalacion(tmp_path) as sesion:
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
    viejo = (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii")
    (tmp_path / "instalacion.db").unlink()  # la base se recrea; el .txt se queda
    with instalacion(tmp_path) as sesion:
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
        nuevo = (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii")
        assert FORMATO.fullmatch(nuevo) and nuevo != viejo
        with pytest.raises(cuentas.ErrorDeAcceso):  # esta base no conoce el viejo
            _reclamar(sesion, viejo, tmp_path)
        assert _reclamar(sesion, nuevo, tmp_path).login == "dueno"


def test_una_base_restaurada_con_otro_codigo_vigente_se_reemite_y_queda_uno(
    tmp_path: Path,
) -> None:
    with instalacion(tmp_path) as sesion:
        cuentas.emitir_codigo(sesion, tmp_path, AHORA)  # el vigente de la base restaurada
        (tmp_path / "codigo_instalacion.txt").write_text(RANCIO, encoding="ascii")
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
        assert _filas(sesion) == 2 and _vigentes(sesion) == 1
        nuevo = (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii")
        assert _reclamar(sesion, nuevo, tmp_path).login == "dueno"


def test_un_archivo_ilegible_o_vacio_tambien_se_reemplaza(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        (tmp_path / "codigo_instalacion.txt").write_bytes(b"\xff\xfe basura \x00")
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
        assert FORMATO.fullmatch((tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii"))
        (tmp_path / "codigo_instalacion.txt").write_text("", encoding="ascii")
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is True
        assert _vigentes(sesion) == 1


def test_un_restablecimiento_caducado_sin_cuentas_se_reemplaza(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        cuentas.emitir_codigo_de_restablecimiento(sesion, tmp_path, AHORA)
        tarde = AHORA + timedelta(hours=24)  # a las 24 h exactas ya no sirve
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, tarde) is True
        assert _vigentes(sesion) == 1
        nuevo = (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii")
        assert _reclamar(sesion, nuevo, tmp_path).login == "dueno"


def test_un_archivo_editado_a_mano_con_el_codigo_vigente_no_se_toca(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA)
        archivo = tmp_path / "codigo_instalacion.txt"
        anotado = "Código: " + archivo.read_text(encoding="ascii").lower()
        archivo.write_text(anotado, encoding="utf-8")
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is False
        assert archivo.read_text(encoding="utf-8") == anotado
        assert _filas(sesion) == 1


def test_con_cuentas_el_archivo_del_restablecimiento_no_se_toca(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        primer_arranque.emitir_restablecimiento(sesion, tmp_path, AHORA)
        escrito = (tmp_path / "codigo_instalacion.txt").read_bytes()
        antes = _filas(sesion)
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is False
        assert (tmp_path / "codigo_instalacion.txt").read_bytes() == escrito
        assert _filas(sesion) == antes


def test_con_cuentas_un_archivo_ajeno_no_se_toca(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        (tmp_path / "codigo_instalacion.txt").write_text(RANCIO, encoding="ascii")
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA) is False
        assert (tmp_path / "codigo_instalacion.txt").read_text(encoding="ascii") == RANCIO


def test_el_estado_dice_solo_tres_cosas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with instalacion(tmp_path) as sesion:
        monkeypatch.setattr(config, "es_producto", lambda raiz=None: False)
        vacio = primer_arranque.estado(sesion, tmp_path)
        assert (vacio.sin_cuentas, vacio.archivo_presente) == (True, False)
        assert vacio.modo == "desarrollo"
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


# --- sobre la instalación de la carpeta de datos -------------------------------------------


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


def test_con_esperar_la_orden_pide_una_tecla_antes_de_cerrar(datos, monkeypatch) -> None:
    with sesion_de_instalacion() as sesion:
        administrador(sesion, datos)
    pedidos: list[str] = []
    monkeypatch.setattr("builtins.input", lambda aviso="": pedidos.append(aviso) or "")
    assert cli.main(["restablecer-administrador", "--esperar"]) == 0
    assert len(pedidos) == 1 and "Enter" in pedidos[0]
    pedidos.clear()
    assert cli.main(["restablecer-administrador"]) == 0
    assert pedidos == []  # desde una consola abierta no se espera
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


# --- el archivo se escribe con el bloqueo tomado y antes de confirmar (observacion de robustez) ---
#
# Antes `emitir_codigo` confirmaba y soltaba el bloqueo y DESPUES escribia el archivo: con dos
# arranques a la vez el segundo podia reemitir (e invalidar el primero) y el archivo quedar con un
# codigo invalidado. Ahora el archivo se escribe (atomico) mientras se tiene el bloqueo.


def test_el_archivo_ya_esta_escrito_cuando_la_base_confirma(tmp_path: Path) -> None:
    from sqlalchemy import event

    vistos: list[str | None] = []
    with instalacion(tmp_path) as sesion:
        archivo = tmp_path / "codigo_instalacion.txt"

        def al_confirmar(_sesion) -> None:
            vistos.append(archivo.read_text(encoding="ascii") if archivo.exists() else None)

        event.listen(sesion, "before_commit", al_confirmar)
        assert primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA)
        assert vistos and vistos[-1] is not None and FORMATO.fullmatch(vistos[-1])
        assert vistos[-1] == archivo.read_text(encoding="ascii")  # el que confirmo es el que queda


def test_si_falla_escribir_el_archivo_la_base_queda_sin_el_codigo_nuevo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with instalacion(tmp_path) as sesion:
        primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA)
        archivo = tmp_path / "codigo_instalacion.txt"
        antes = archivo.read_text(encoding="ascii")
        archivo.unlink()  # fuerza la reemision
        archivo.write_text("NADA-QUE-VER\n", encoding="ascii")

        def falla(*_a, **_k):
            raise OSError("disco lleno")

        monkeypatch.setattr(cuentas.os, "replace", falla)
        with pytest.raises(OSError):
            primer_arranque.asegurar_codigo(sesion, tmp_path, AHORA + timedelta(hours=1))
        monkeypatch.undo()
        assert (
            _filas(sesion) == 1 and _vigentes(sesion) == 1
        )  # ni fila nueva ni anterior invalidada
        assert sesion.scalar(select(CodigoInstalacion.huella)) == cuentas._huella_codigo(antes)
        assert archivo.read_text(encoding="ascii") == "NADA-QUE-VER\n"  # el archivo no se tocó
        assert [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"] == []  # sin temporales
