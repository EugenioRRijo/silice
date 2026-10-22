"""Códigos de instalación y de restablecimiento (BCP-1; diseño §3.3, §3.4 y §16 hallazgo 2).

Cada prueba fija su oráculo a mano:

- emitir un código invalida los pendientes anteriores (`usado` = el instante de la emisión nueva);
- el código de RESTABLECIMIENTO caduca a las 24 h exactas (23:59:59 sirve; 24:00:00 ya no) con el
  reloj inyectado; el de la primera vez no caduca;
- `preparar_primera_vez` reemite si no hay cuentas y falta el archivo (aunque haya un código
  vigente en la base: hoy devuelve `None` y nadie reescribe el archivo borrado);
- emitir, preparar y reclamar toman el bloqueo de escritura: con una escritura ajena abierta
  vencen con `MENSAJE_BASE_OCUPADA` (la ruta lo responde 503);
- `ademas_arma` da `arma,administrador` solo a la cuenta NUEVA;
- un restablecimiento que cambia de rol a una cuenta existente deja el evento «promovida a
  administrador» (tipo `cambio de roles`) sin el código.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select, text

from seguridad import cuentas
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Base, CodigoInstalacion, EventoAcceso, IntentoAcceso, Usuario
from tests.fixtures.instalacion import (
    AHORA,
    CONTRASENA,
    administrador,
    instalacion,
    persona,
)

OTRA = "otra contrasena larga distinta"


@pytest.fixture
def freno() -> cuentas.FrenoGlobal:
    return cuentas.FrenoGlobal()


def _filas(sesion) -> list[CodigoInstalacion]:
    return list(sesion.scalars(select(CodigoInstalacion).order_by(CodigoInstalacion.creado)))


# --- emitir invalida los pendientes -----------------------------------------------------------


def test_emitir_un_codigo_invalida_los_pendientes_anteriores(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        viejo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        nuevo = cuentas.emitir_codigo(sesion, tmp_path, AHORA + timedelta(minutes=5))
        antiguas, ultima = _filas(sesion)
        assert antiguas.usado == AHORA + timedelta(minutes=5)  # invalidado al emitir el nuevo
        assert ultima.usado is None
        with pytest.raises(cuentas.ErrorDeAcceso, match="código de instalación"):
            cuentas.reclamar_instalacion(
                sesion, viejo, "uno", "U", CONTRASENA, AHORA, tmp_path, freno=freno
            )
        usuario = cuentas.reclamar_instalacion(
            sesion, nuevo, "uno", "U", CONTRASENA, AHORA, tmp_path, freno=freno
        )
        assert usuario.login == "uno"


def test_el_archivo_lleva_siempre_el_ultimo_codigo(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        nuevo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        texto = (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).read_text(encoding="ascii")
        assert texto == "-".join(nuevo[i : i + 4] for i in range(0, 20, 4)) + "\n"


# --- caducidad del código de restablecimiento ---------------------------------------------------


@pytest.mark.parametrize(
    ("pasado", "sirve"),
    [
        (timedelta(hours=23, minutes=59, seconds=59), True),
        (timedelta(hours=24), False),
        (timedelta(hours=24, seconds=1), False),
        (timedelta(days=30), False),
    ],
)
def test_el_codigo_de_restablecimiento_caduca_a_las_24_horas(
    tmp_path: Path, freno, pasado: timedelta, sirve: bool
) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        rescate = cuentas.emitir_codigo_de_restablecimiento(sesion, tmp_path, AHORA)
        reclamo = lambda: cuentas.reclamar_instalacion(  # noqa: E731
            sesion, rescate, admin.login, "Admin", OTRA, AHORA + pasado, tmp_path, freno=freno
        )
        if sirve:
            assert reclamo().id == admin.id
            return
        with pytest.raises(cuentas.ErrorDeAcceso) as error:
            reclamo()
        assert str(error.value) == cuentas.MENSAJE_CODIGO  # el mismo texto que un código errado
        assert not isinstance(error.value, cuentas.CuentaBloqueada)
        sesion.refresh(admin)
        assert cuentas._coincide(admin.huella_clave, CONTRASENA)  # la contraseña no cambió
        assert sesion.get(IntentoAcceso, cuentas.CLAVE_INTENTOS_CODIGO).fallos_seguidos == 1


def test_el_codigo_de_la_primera_vez_no_caduca(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        usuario = cuentas.reclamar_instalacion(
            sesion, codigo, "uno", "U", CONTRASENA, AHORA + timedelta(days=90), tmp_path,
            freno=freno,
        )
        assert usuario.login == "uno"


# --- reemisión cuando falta el archivo ------------------------------------------------------------


def test_sin_cuentas_y_sin_archivo_preparar_reemite_e_invalida_el_codigo_anterior(
    tmp_path: Path, freno
) -> None:
    with instalacion(tmp_path) as sesion:
        primero = cuentas.preparar_primera_vez(sesion, tmp_path, AHORA)
        assert primero is not None
        assert cuentas.preparar_primera_vez(sesion, tmp_path, AHORA) is None  # hay archivo
        (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).unlink()  # alguien lo borró
        segundo = cuentas.preparar_primera_vez(sesion, tmp_path, AHORA + timedelta(minutes=1))
        assert segundo is not None and segundo != primero
        assert (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).is_file()
        vigentes = [f for f in _filas(sesion) if f.usado is None]
        assert len(vigentes) == 1  # el anterior quedó invalidado
        with pytest.raises(cuentas.ErrorDeAcceso):
            cuentas.reclamar_instalacion(
                sesion, primero, "uno", "U", CONTRASENA, AHORA, tmp_path, freno=freno
            )


def test_con_cuentas_preparar_no_emite_aunque_falte_el_archivo(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        assert cuentas.preparar_primera_vez(sesion, tmp_path, AHORA) is None
        assert not (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).exists()


# --- bloqueo de escritura --------------------------------------------------------------------


def _escritor_ajeno(motor):
    """Otra conexión con el bloqueo de escritura tomado (una escritura que no termina)."""
    conexion = motor.raw_connection()
    conexion.cursor().execute("BEGIN IMMEDIATE")
    return conexion


@pytest.mark.parametrize("operacion", ["emitir", "preparar", "reclamar", "restablecimiento"])
def test_con_una_escritura_ajena_abierta_vence_con_base_ocupada(
    tmp_path: Path, operacion: str
) -> None:
    motor = crear_motor(tmp_path / "instalacion.db")
    Base.metadata.create_all(motor)
    ajeno = None
    try:
        with abrir_sesion(motor) as sesion:
            codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        ajeno = _escritor_ajeno(motor)
        with abrir_sesion(motor) as sesion:
            sesion.execute(text("PRAGMA busy_timeout=50"))  # la espera de la prueba, no 5 s
            llamadas = {
                "emitir": lambda: cuentas.emitir_codigo(sesion, tmp_path, AHORA),
                "preparar": lambda: cuentas.preparar_primera_vez(sesion, tmp_path, AHORA),
                "reclamar": lambda: cuentas.reclamar_instalacion(
                    sesion, codigo, "uno", "U", CONTRASENA, AHORA, tmp_path,
                    freno=cuentas.FrenoGlobal(),
                ),
                "restablecimiento": lambda: cuentas.emitir_codigo_de_restablecimiento(
                    sesion, tmp_path, AHORA
                ),
            }
            if operacion == "preparar":  # sin archivo, para que intente emitir
                (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).unlink()
            with pytest.raises(ValueError, match="La base está ocupada") as error:
                llamadas[operacion]()
            assert str(error.value) == cuentas.MENSAJE_BASE_OCUPADA
    finally:
        if ajeno is not None:
            ajeno.rollback()
            ajeno.close()
        motor.dispose()


# --- ademas_arma y promoción ----------------------------------------------------------------------


def test_ademas_arma_da_los_dos_roles_a_la_cuenta_nueva(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        usuario = cuentas.reclamar_instalacion(
            sesion, codigo, "solo", "Solo", CONTRASENA, AHORA, tmp_path, freno=freno,
            ademas_arma=True,
        )
        assert usuario.roles == "arma,administrador"  # el orden de `Rol`


def test_sin_ademas_arma_la_cuenta_nueva_es_solo_administradora(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        usuario = cuentas.reclamar_instalacion(
            sesion, codigo, "solo", "Solo", CONTRASENA, AHORA, tmp_path, freno=freno
        )
        assert usuario.roles == "administrador"


def _eventos(sesion, tipo: str) -> list[EventoAcceso]:
    return list(sesion.scalars(select(EventoAcceso).where(EventoAcceso.tipo == tipo)))


def test_un_restablecimiento_que_promueve_una_cuenta_deja_el_evento(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        ana = persona(sesion, admin, "ana", ("arma",))
        rescate = cuentas.emitir_codigo_de_restablecimiento(sesion, tmp_path, AHORA)
        cuentas.reclamar_instalacion(
            sesion, rescate, "ana", "Ana", OTRA, AHORA, tmp_path, freno=freno, ademas_arma=True
        )
        sesion.refresh(ana)
        assert ana.roles == "arma,administrador"  # `ademas_arma` no cambia nada más
        promovidas = [e for e in _eventos(sesion, "cambio de roles") if "promovida" in e.detalle]
        assert len(promovidas) == 1
        assert promovidas[0].login_intentado == "ana"
        assert promovidas[0].usuario_id == ana.id
        assert "promovida a administrador" in promovidas[0].detalle
        assert rescate not in promovidas[0].detalle


def test_un_restablecimiento_de_un_administrador_no_deja_evento_de_promocion(
    tmp_path: Path, freno
) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        rescate = cuentas.emitir_codigo_de_restablecimiento(sesion, tmp_path, AHORA)
        cuentas.reclamar_instalacion(
            sesion, rescate, admin.login, "Admin", OTRA, AHORA, tmp_path, freno=freno,
            ademas_arma=True,
        )
        sesion.refresh(admin)
        assert admin.roles == "administrador"  # `ademas_arma` solo vale para la cuenta nueva
        assert [e for e in _eventos(sesion, "cambio de roles") if "promovida" in e.detalle] == []


def test_el_codigo_no_aparece_en_ningun_evento(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        persona(sesion, admin, "ana", ("arma",))
        rescate = cuentas.emitir_codigo_de_restablecimiento(sesion, tmp_path, AHORA)
        cuentas.reclamar_instalacion(
            sesion, rescate, "ana", "Ana", OTRA, AHORA, tmp_path, freno=freno
        )
        todos = sesion.scalars(select(EventoAcceso)).all()
        usuarios = sesion.scalars(select(Usuario)).all()
        assert todos and usuarios
        for evento in todos:
            assert rescate not in f"{evento.login_intentado}{evento.detalle}{evento.ip_cliente}"
