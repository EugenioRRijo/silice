"""Carrera en `reclamar_instalacion` (BCP-1, S3 del diseño; expediente en
`docs/bitacora/2026-10-21-bcp1-expediente-seguridad.md`).

Dos hilos reclaman a la vez el MISMO código de instalación, cada uno con su sesión y su conexión a
la misma `instalacion.db`. Un código de un solo uso debe producir exactamente UNA cuenta; el
perdedor recibe el rechazo de siempre (`MENSAJE_CODIGO`), nunca un error de la base.

Oráculos a mano (ninguno sale del código bajo prueba): el número de filas de `usuario`, el de
códigos con `usado` fijado y que el archivo del código ya no exista. Los tres escenarios:

- (a) con una fila previa en `intento_acceso` (basta UN fallo anterior): sin bloqueo de escritura
  antes de leer, los dos pasan la comprobación y se crean dos administradores;
- (b) sin fila previa: el perdedor choca en el INSERT del contador y la base le levanta
  `IntegrityError` (en la API, un 500);
- (c) el mismo login en los dos hilos: nunca un error de la base.

La defensa extra (`UPDATE ... WHERE usado IS NULL` con una sola fila afectada) se prueba apagando
el bloqueo de escritura: aun así el segundo reclamo no puede crear su cuenta.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select

from seguridad import cuentas
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Base, CodigoInstalacion, Usuario
from tests.fixtures.instalacion import AHORA, CONTRASENA


@contextmanager
def _motor(carpeta: Path) -> Iterator[Engine]:
    carpeta.mkdir(parents=True, exist_ok=True)
    motor = crear_motor(carpeta / "instalacion.db")
    Base.metadata.create_all(motor)
    try:
        yield motor
    finally:
        motor.dispose()


def _carrera(
    motor: Engine, carpeta: Path, logins: tuple[str, str], *, con_fila_previa: bool
) -> list[tuple[str, str]]:
    """Dos reclamos simultáneos del mismo código; `(clase del resultado, mensaje)` de cada hilo."""
    with abrir_sesion(motor) as sesion:
        codigo = cuentas.emitir_codigo(sesion, carpeta, AHORA)
        if con_fila_previa:  # un solo fallo anterior crea la fila del contador del código
            with pytest.raises(cuentas.ErrorDeAcceso):
                cuentas.reclamar_instalacion(
                    sesion,
                    "A" * 20,
                    "previo",
                    "P",
                    CONTRASENA,
                    AHORA,
                    carpeta,
                    freno=cuentas.FrenoGlobal(),
                )
    barrera = threading.Barrier(2)
    resultados: list[tuple[str, str]] = []
    candado = threading.Lock()

    def reclamar(login: str) -> None:
        with abrir_sesion(motor) as sesion:
            barrera.wait(timeout=10)
            try:
                cuentas.reclamar_instalacion(
                    sesion,
                    codigo,
                    login,
                    "Nombre",
                    CONTRASENA,
                    AHORA,
                    carpeta,
                    freno=cuentas.FrenoGlobal(),
                    dormir=lambda segundos: None,
                )
                resultado = ("ok", login)
            except Exception as error:  # noqa: BLE001 - el tipo del error ES lo que se mide
                resultado = (type(error).__name__, str(error))
        with candado:
            resultados.append(resultado)

    hilos = [threading.Thread(target=reclamar, args=(login,)) for login in logins]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)
    assert not any(hilo.is_alive() for hilo in hilos)
    return sorted(resultados)


def _cuentas_y_codigos(motor: Engine) -> tuple[int, int]:
    with abrir_sesion(motor) as sesion:
        usuarios = sesion.scalar(select(func.count()).select_from(Usuario))
        usados = sesion.scalar(
            select(func.count())
            .select_from(CodigoInstalacion)
            .where(CodigoInstalacion.usado.is_not(None))
        )
    return usuarios, usados


@pytest.mark.parametrize(
    ("con_fila_previa", "logins"),
    [
        pytest.param(True, ("uno", "dos"), id="a-con-fila-previa-logins-distintos"),
        pytest.param(False, ("uno", "dos"), id="b-sin-fila-previa-logins-distintos"),
        pytest.param(True, ("uno", "uno"), id="c-con-fila-previa-mismo-login"),
        pytest.param(False, ("uno", "uno"), id="c-sin-fila-previa-mismo-login"),
    ],
)
def test_dos_reclamos_simultaneos_crean_una_sola_cuenta(
    tmp_path: Path, con_fila_previa: bool, logins: tuple[str, str]
) -> None:
    with _motor(tmp_path) as motor:
        resultados = _carrera(motor, tmp_path, logins, con_fila_previa=con_fila_previa)
        usuarios, usados = _cuentas_y_codigos(motor)
    clases = sorted(clase for clase, _ in resultados)
    assert clases == ["ErrorDeAcceso", "ok"], resultados  # un éxito y un rechazo; nunca un 500
    assert ("ErrorDeAcceso", cuentas.MENSAJE_CODIGO) in resultados
    assert usuarios == 1  # un solo administrador con un solo código
    assert usados == 1  # una sola fila con `usado` fijado
    assert not (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).exists()


def test_la_defensa_del_update_basta_aunque_falle_el_bloqueo_de_escritura(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sin `_tomar_escritura` (simula que no se pudo tomar) el `UPDATE ... usado IS NULL` con
    `rowcount == 1` deja pasar a uno solo, y el segundo no deja ninguna cuenta a medias."""
    sin_bloqueo: Callable[[object], None] = lambda sesion: None  # noqa: E731
    monkeypatch.setattr(cuentas, "_tomar_escritura", sin_bloqueo)
    with _motor(tmp_path) as motor:
        resultados = _carrera(motor, tmp_path, ("uno", "dos"), con_fila_previa=True)
        usuarios, usados = _cuentas_y_codigos(motor)
    assert sorted(clase for clase, _ in resultados) == ["ErrorDeAcceso", "ok"], resultados
    assert ("ErrorDeAcceso", cuentas.MENSAJE_CODIGO) in resultados
    assert usuarios == 1
    assert usados == 1
