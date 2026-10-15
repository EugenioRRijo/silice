"""`scripts/restablecer_administrador.py`: devolver el acceso con acceso al equipo (S3 §5.4 y §5.5).

Todo ocurre en `tmp_path` (`SILICE_DATOS` y `SILICE_INSTALACION` apuntan allí): nunca en `data/`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from scripts import restablecer_administrador as script
from seguridad import cuentas, sesiones
from seguridad.modelo import CodigoInstalacion, EventoAcceso, Sesion, Usuario
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

RAIZ = Path(__file__).resolve().parents[2]
BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # RFC 4648: 32 símbolos = 5 bits cada uno
NUEVA = "otra contrasena larga y nueva"


@pytest.fixture
def instalacion_con_gente(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path))
    monkeypatch.setenv("SILICE_INSTALACION", str(tmp_path / "instalacion.db"))
    cerrar_motores()
    with sesion_de_instalacion() as bd:
        admin = administrador(bd, tmp_path)
        luis = persona(bd, admin, "luis", ("arma",))
        fichas = (sesiones.abrir(bd, admin, AHORA), sesiones.abrir(bd, luis, AHORA))
    yield tmp_path, fichas
    cerrar_motores()


def test_emite_un_codigo_cierra_las_sesiones_de_los_administradores_y_deja_registro(
    instalacion_con_gente,
) -> None:
    carpeta, (ficha_admin, ficha_luis) = instalacion_con_gente
    codigo, archivo = script.restablecer(AHORA)
    assert len(codigo) == 20 and archivo == carpeta / "codigo_instalacion.txt"
    assert archivo.read_text(encoding="ascii").replace("-", "").strip() == codigo
    with sesion_de_instalacion() as bd:
        assert sesiones.validar(bd, ficha_admin, AHORA) is None  # la del administrador, cerrada
        assert sesiones.validar(bd, ficha_luis, AHORA) is not None  # la de Luis sigue
        [fila] = bd.query(CodigoInstalacion).filter_by(motivo="restablecimiento").all()
        assert fila.usado is None and fila.creado == AHORA
        eventos = bd.query(EventoAcceso).filter_by(tipo="codigo de instalacion")
        assert "restablecimiento" in [e.detalle for e in eventos]
        cerradas = bd.query(Sesion).filter_by(cerrada=True, motivo_cierre="restablecimiento")
        assert cerradas.count() == 1


def test_el_codigo_tiene_100_bits_y_la_base_guarda_solo_su_huella(instalacion_con_gente):
    carpeta, _ = instalacion_con_gente
    codigo, archivo = script.restablecer(AHORA)
    assert len(codigo) == 20 and set(codigo) <= set(BASE32)  # 20 x 5 bits = 100 bits
    # el archivo lo trae en grupos de cuatro para leerlo: XXXX-XXXX-XXXX-XXXX-XXXX
    escrito = archivo.read_text(encoding="ascii").strip()
    assert [len(g) for g in escrito.split("-")] == [4, 4, 4, 4, 4]
    with sesion_de_instalacion() as bd:
        fila = bd.query(CodigoInstalacion).filter_by(motivo="restablecimiento").one()
        assert fila.huella != codigo and codigo not in fila.huella and len(fila.huella) == 64
        assert all(codigo not in (e.detalle or "") for e in bd.query(EventoAcceso))
    bruto = b"".join(p.read_bytes() for p in sorted(carpeta.glob("instalacion.db*")))
    assert codigo.encode() not in bruto and escrito.encode() not in bruto


def test_veinte_restablecimientos_dan_veinte_codigos_distintos(instalacion_con_gente) -> None:
    codigos = {script.restablecer(AHORA + timedelta(seconds=i))[0] for i in range(20)}
    assert len(codigos) == 20


def test_cierra_las_sesiones_de_todos_los_administradores(instalacion_con_gente) -> None:
    _, (ficha_admin, ficha_luis) = instalacion_con_gente
    with sesion_de_instalacion() as bd:
        admin = bd.query(Usuario).filter_by(login="admin").one()
        maria = persona(bd, admin, "maria", ("administrador", "revisa"))
        ficha_maria = sesiones.abrir(bd, maria, AHORA)
        otra_de_admin = sesiones.abrir(bd, admin, AHORA)
    script.restablecer(AHORA)
    with sesion_de_instalacion() as bd:
        for ficha in (ficha_admin, otra_de_admin, ficha_maria):
            assert sesiones.validar(bd, ficha, AHORA) is None
        assert sesiones.validar(bd, ficha_luis, AHORA) is not None
        cerradas = bd.query(Sesion).filter_by(cerrada=True, motivo_cierre="restablecimiento")
        assert cerradas.count() == 3
        # las cuentas no cambian: solo se cierran sus sesiones
        assert bd.query(Usuario).count() == 3
        assert all(u.activo for u in bd.query(Usuario))


def test_con_el_codigo_se_recupera_la_cuenta_aunque_ya_haya_usuarios(
    instalacion_con_gente,
) -> None:
    carpeta, _ = instalacion_con_gente
    codigo, _ = script.restablecer(AHORA)
    with sesion_de_instalacion() as bd:
        usuario = cuentas.reclamar_instalacion(
            bd,
            codigo,
            "admin",
            "Admin de Prueba",
            NUEVA,
            AHORA,
            carpeta,
            freno=cuentas.FrenoGlobal(),
        )
        assert usuario.login == "admin" and bd.query(Usuario).count() == 2
        assert "administrador" in usuario.roles.split(",")
        assert not (carpeta / "codigo_instalacion.txt").exists()  # el código se usó y se borró
        fila = bd.query(CodigoInstalacion).filter_by(motivo="restablecimiento").one()
        assert fila.usado == AHORA
        with pytest.raises(cuentas.ErrorDeAcceso):  # y no sirve dos veces
            cuentas.reclamar_instalacion(
                bd,
                codigo,
                "admin",
                "Admin de Prueba",
                NUEVA,
                AHORA,
                carpeta,
                freno=cuentas.FrenoGlobal(),
                dormir=lambda segundos: None,
            )
        entra = cuentas.autenticar(bd, "admin", NUEVA, AHORA, freno=cuentas.FrenoGlobal())
        assert entra.login == "admin"
        with pytest.raises(cuentas.ErrorDeAcceso):  # la contraseña perdida ya no sirve
            cuentas.autenticar(
                bd,
                "admin",
                CONTRASENA,
                AHORA,
                freno=cuentas.FrenoGlobal(),
                dormir=lambda segundos: None,
            )
    assert CONTRASENA != NUEVA


def test_el_codigo_de_restablecimiento_no_sirve_para_otra_cosa_que_un_administrador(
    instalacion_con_gente,
) -> None:
    """Con el código, quien lo use queda como administrador (no hereda los roles de otro)."""
    carpeta, _ = instalacion_con_gente
    codigo, _ = script.restablecer(AHORA)
    with sesion_de_instalacion() as bd:
        nuevo = cuentas.reclamar_instalacion(
            bd, codigo, "rosa", "Rosa", NUEVA, AHORA, carpeta, freno=cuentas.FrenoGlobal()
        )
        assert nuevo.roles == "administrador" and bd.query(Usuario).count() == 3


def test_un_codigo_inventado_no_restablece(instalacion_con_gente) -> None:
    carpeta, _ = instalacion_con_gente
    script.restablecer(AHORA)
    with sesion_de_instalacion() as bd, pytest.raises(cuentas.ErrorDeAcceso):
        cuentas.reclamar_instalacion(
            bd,
            "A" * 20,
            "admin",
            "Admin",
            NUEVA,
            AHORA,
            carpeta,
            freno=cuentas.FrenoGlobal(),
            dormir=lambda segundos: None,
        )


def test_la_consola_muestra_el_codigo_y_donde_esta(instalacion_con_gente, capsys) -> None:
    carpeta, _ = instalacion_con_gente
    assert script.main([]) == 0
    salida = capsys.readouterr().out
    assert "Código de instalación nuevo" in salida and "codigo_instalacion.txt" in salida
    assert "sesiones de los administradores quedaron cerradas" in salida
    # lo que se imprime es lo mismo que quedó en el archivo
    escrito = (carpeta / "codigo_instalacion.txt").read_text(encoding="ascii").strip()
    assert escrito in salida


def test_el_script_no_toca_la_hora_de_otros_eventos(instalacion_con_gente) -> None:
    antes = datetime.now()
    script.restablecer()
    despues = datetime.now()
    with sesion_de_instalacion() as bd:
        ultimo = bd.query(EventoAcceso).order_by(EventoAcceso.id.desc()).first()
        assert ultimo.tipo == "codigo de instalacion" and ultimo.detalle == "restablecimiento"
        assert antes.replace(microsecond=0) <= ultimo.fecha_hora <= despues
        # los eventos anteriores conservan su hora (la de la fixture)
        previos = bd.query(EventoAcceso).filter(EventoAcceso.id < ultimo.id).all()
        assert previos and all(e.fecha_hora == AHORA for e in previos)


def test_el_script_corre_solo_desde_la_consola(instalacion_con_gente) -> None:
    """`python scripts/restablecer_administrador.py` en un proceso aparte, sobre `tmp_path`."""
    carpeta, (ficha_admin, _) = instalacion_con_gente
    cerrar_motores()  # el proceso hijo abre la base por su cuenta
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    assert entorno["SILICE_DATOS"] == str(carpeta)
    resultado = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "restablecer_administrador.py")],
        cwd=carpeta,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    escrito = (carpeta / "codigo_instalacion.txt").read_text(encoding="ascii").strip()
    assert escrito in resultado.stdout
    with sesion_de_instalacion() as bd:
        assert sesiones.validar(bd, ficha_admin, AHORA) is None
        assert bd.query(CodigoInstalacion).filter_by(motivo="restablecimiento").count() == 1


def test_el_script_help_sale_con_cero_sin_emitir_codigo(instalacion_con_gente) -> None:
    """`python scripts/restablecer_administrador.py --help` muestra la ayuda y sale con 0."""
    carpeta, _ = instalacion_con_gente
    cerrar_motores()
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    resultado = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "restablecer_administrador.py"), "--help"],
        cwd=carpeta,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert not (carpeta / "codigo_instalacion.txt").exists()
    assert "usage:" in resultado.stdout or "uso:" in resultado.stdout.lower()
    with sesion_de_instalacion() as bd:
        assert bd.query(CodigoInstalacion).filter_by(motivo="restablecimiento").count() == 0
