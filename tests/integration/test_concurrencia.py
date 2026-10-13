"""SL-E12: varios usuarios a la vez sobre SQLite (RF-83, RNF-16; spec S3 §6.3 y §13.4, PRU-H20).

Sin tiempos de espera fijos: tres hilos sincronizados con `threading.Barrier`, un número fijo de
guardados por hilo, y se cuentan filas. Lo esperado es exactamente 1 + 3 x N versiones y 3 x N
`RegistroCambio`, una cadena lineal y ningún `database is locked`. Cada base vive en `tmp_path`.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from core import models
from core.budget import cadena
from core.catalog import abrir_sesion, abrir_sesion_de_escritura, crear_esquema, crear_motor
from core.catalog import sesion as modulo_sesion
from core.models.cadena import EslabonVersion
from tests.fixtures.canonico_minimo import guardar_otra, registro, sembrar_minimo

HILOS, GUARDADOS = 3, 10


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'caso.db').as_posix()}"


def _base(tmp_path: Path):
    motor = crear_motor(_url(tmp_path))
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        proyecto, v1, lista = sembrar_minimo(sesion)
        sesion.commit()
        return motor, proyecto.id, lista.id, v1.id


def test_el_motor_usa_wal_espera_y_claves_foraneas(tmp_path: Path) -> None:
    motor = crear_motor(_url(tmp_path))
    try:
        with motor.connect() as conexion:
            assert conexion.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            assert conexion.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000
            assert modulo_sesion.ESPERA_OCUPADA_MS == 5000  # SUPUESTO_DECLARADO de S3 §4.4
            assert conexion.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    finally:
        motor.dispose()


def test_la_sesion_de_escritura_toma_el_bloqueo_al_empezar(tmp_path: Path, monkeypatch) -> None:
    """Dos sesiones de escritura no pueden estar abiertas a la vez: la segunda espera, y si la
    espera se agota, falla con `database is locked` (prueba de que fue `BEGIN IMMEDIATE`). Un
    `SELECT` en una transacción `BEGIN` diferida no tomaría el bloqueo."""
    monkeypatch.setattr(modulo_sesion, "ESPERA_OCUPADA_MS", 50)
    motor = crear_motor(_url(tmp_path))
    crear_esquema(motor)
    primera, segunda = abrir_sesion_de_escritura(motor), abrir_sesion_de_escritura(motor)
    lectora = abrir_sesion(motor)
    try:
        primera.execute(text("SELECT 1"))  # empieza la transacción: ya tiene el bloqueo
        with pytest.raises(OperationalError, match="locked"):
            segunda.execute(text("SELECT 1"))
        assert lectora.execute(text("SELECT count(*) FROM proyecto")).scalar() == 0  # WAL: lee
    finally:
        for sesion in (primera, segunda, lectora):
            sesion.rollback()
            sesion.close()
        motor.dispose()


def test_una_sesion_de_lectura_no_toma_el_bloqueo_de_escritura(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(modulo_sesion, "ESPERA_OCUPADA_MS", 50)
    motor = crear_motor(_url(tmp_path))
    crear_esquema(motor)
    uno, otro = abrir_sesion(motor), abrir_sesion(motor)
    try:
        uno.execute(text("SELECT 1"))
        otro.execute(text("SELECT 1"))  # no espera ni falla
    finally:
        uno.close()
        otro.close()
        motor.dispose()


def test_la_segunda_escritura_espera_y_entra_cuando_la_primera_confirma(tmp_path: Path) -> None:
    """La espera (`busy_timeout`) es la que hace que nadie vea `database is locked`: un hilo
    toma el bloqueo, otro lo pide y queda esperando; al confirmar el primero, el segundo entra."""
    motor, proyecto_id, lista_id, _ = _base(tmp_path)
    tomado, pide, liberar = threading.Event(), threading.Event(), threading.Event()
    errores, orden = [], []

    def primero() -> None:
        with abrir_sesion_de_escritura(motor) as sesion:
            sesion.execute(text("SELECT 1"))
            tomado.set()
            liberar.wait(timeout=5)
            orden.append("primero")
            sesion.commit()

    def segundo() -> None:
        tomado.wait(timeout=5)
        try:
            with abrir_sesion_de_escritura(motor) as sesion:
                pide.set()
                sesion.execute(text("SELECT 1"))  # espera aquí hasta que el primero confirma
                orden.append("segundo")
                sesion.commit()
        except Exception as error:  # noqa: BLE001 - se informa abajo
            errores.append(repr(error))

    hilos = [threading.Thread(target=primero), threading.Thread(target=segundo)]
    for hilo in hilos:
        hilo.start()
    tomado.wait(timeout=5)
    pide.wait(timeout=5)  # el segundo ya pidió el bloqueo (o está por pedirlo) antes de liberar
    liberar.set()
    for hilo in hilos:
        hilo.join(timeout=10)
    motor.dispose()
    assert errores == []
    assert orden == ["primero", "segundo"]


def test_tres_hilos_guardan_diez_versiones_cada_uno_sin_perder_ninguna(tmp_path: Path) -> None:
    motor, proyecto_id, lista_id, _ = _base(tmp_path)
    barrera, errores = threading.Barrier(HILOS), []

    def trabajar(hilo: int) -> None:
        barrera.wait()
        for i in range(GUARDADOS):
            try:
                with abrir_sesion_de_escritura(motor) as sesion:
                    proyecto = sesion.get(models.Proyecto, proyecto_id)
                    lista = sesion.get(models.ListaPrecios, lista_id)
                    origen = sesion.scalars(
                        select(models.Presupuesto).where(models.Presupuesto.codigo == "001")
                    ).one()
                    nueva = guardar_otra(
                        sesion,
                        proyecto,
                        lista,
                        f"H{hilo}-{i:02d}",
                        version_origen=origen,
                        motivo="edicion",
                        usuario=f"hilo{hilo} <h{hilo}>",
                    )
                    sesion.add(registro(proyecto, origen, nueva, responsable=f"hilo{hilo}"))
                    sesion.commit()
            except Exception as error:  # noqa: BLE001 - se cuenta y se informa abajo
                errores.append(repr(error))

    hilos = [threading.Thread(target=trabajar, args=(h,)) for h in range(HILOS)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=120)
    assert not any(hilo.is_alive() for hilo in hilos)
    assert errores == []
    total = HILOS * GUARDADOS  # 30, contado a mano: 3 hilos x 10 guardados
    try:
        with abrir_sesion(motor) as sesion:
            assert sesion.query(models.Presupuesto).count() == 1 + total
            assert sesion.query(models.RegistroCambio).count() == total
            assert sesion.query(EslabonVersion).count() == 1 + total
            proyecto = sesion.get(models.Proyecto, proyecto_id)
            resultado = cadena.verificar_cadena(sesion, proyecto)
            assert resultado.integra and resultado.versiones == 1 + total
            eslabones = cadena.eslabones_de(sesion, proyecto)
            # lineal: cada eslabón cuelga del anterior en el orden de las versiones
            assert [e.anterior for e in eslabones[1:]] == [e.huella_eslabon for e in eslabones[:-1]]
            # cada hilo selló sus diez versiones a su nombre
            por_usuario = {}
            for e in eslabones[1:]:
                por_usuario[e.usuario] = por_usuario.get(e.usuario, 0) + 1
            assert por_usuario == {f"hilo{h} <h{h}>": GUARDADOS for h in range(HILOS)}
    finally:
        motor.dispose()


def test_si_dos_sellaran_sobre_el_mismo_eslabon_el_indice_unico_frena_al_segundo(
    tmp_path: Path,
) -> None:
    """La red de SL-E7 bajo SL-E12: se simula que la segunda transacción leyó una cabeza vieja
    (lo que pasaría sin `BEGIN IMMEDIATE`). El índice único la frena con `SelladoEnConflicto`,
    con el mensaje para el usuario, y la base no se corrompe."""
    motor, proyecto_id, lista_id, v1_id = _base(tmp_path)
    try:
        with abrir_sesion(motor) as sesion:
            genesis_de_v1 = sesion.get(EslabonVersion, v1_id).anterior
        with pytest.MonkeyPatch.context() as parche:
            parche.setattr(cadena, "_cabeza", lambda session, proyecto_id: genesis_de_v1)
            with abrir_sesion_de_escritura(motor) as sesion:
                proyecto = sesion.get(models.Proyecto, proyecto_id)
                lista = sesion.get(models.ListaPrecios, lista_id)
                guardar_otra(sesion, proyecto, lista, "002")
                with pytest.raises(cadena.SelladoEnConflicto, match="Otra persona"):
                    sesion.commit()
                sesion.rollback()
        with abrir_sesion(motor) as sesion:
            assert sesion.query(models.Presupuesto).count() == 1
            proyecto = sesion.get(models.Proyecto, proyecto_id)
            assert cadena.verificar_cadena(sesion, proyecto).integra
    finally:
        motor.dispose()
