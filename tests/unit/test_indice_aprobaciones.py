"""MP-4, Tarea 18: el índice de aprobaciones de la instalación (choque 14 del plan de montar un
presupuesto).

Las aprobaciones viven en cada carpeta de trabajo (la fuente de verdad); «Por aprobar» lista las de
todas, así que `instalacion.db` guarda un reflejo, `mp_indice_aprobacion`, que `reflejar` reescribe
para una carpeta desde su rastro. Bases SQLite en archivo (`tmp_path`): la de la instalación con
la tabla del índice y dos carpetas con la «Vivienda Demo 80 m2» de
`tests/fixtures/carpeta_aprobaciones.py`. Oráculos a mano: los textos, las horas y los estados; el
total de una versión se lee en la prueba con `sqlite3` (Σ `partida_presupuestada.total`, sumado en
`Decimal`), sin pasar por el código bajo prueba.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.orm import Session

from aplicacion import aprobaciones, indice_aprobaciones
from aplicacion.indice_aprobaciones import FilaIndice
from aplicacion.tablas_aprobacion import crear_esquema_aprobacion
from aplicacion.tablas_indice_aprobacion import METADATA_INDICE_APROBACION
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from tests.fixtures.carpeta_aprobaciones import ANA, OBRA, guardar_version, sembrar_vivienda

RITA = "Rita <rita>"
LUNES = datetime(2026, 10, 19, 9, 0)
MARTES = datetime(2026, 10, 20, 10, 30)
MIERCOLES = datetime(2026, 10, 21, 11, 15)
JUEVES = datetime(2026, 10, 22, 16, 45)


def _carpeta(ruta: Path) -> Engine:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    crear_esquema_aprobacion(motor)
    with abrir_sesion(motor) as s:
        sembrar_vivienda(s)
    return motor


@pytest.fixture
def carpetas(tmp_path: Path) -> Iterator[dict[str, Engine]]:
    motores = {"a.db": _carpeta(tmp_path / "a.db"), "b.db": _carpeta(tmp_path / "b.db")}
    try:
        yield motores
    finally:
        for motor in motores.values():
            motor.dispose()


@pytest.fixture
def instalacion(tmp_path: Path) -> Iterator[Session]:
    motor = create_engine(f"sqlite:///{(tmp_path / 'instalacion.db').as_posix()}")
    METADATA_INDICE_APROBACION.create_all(motor)
    try:
        with Session(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


def _total(motor: Engine, version: str) -> Decimal:
    """Σ de los totales guardados de la versión, leídos con `sqlite3` y sumados en `Decimal`."""
    ruta = motor.url.database
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(
            "SELECT pp.total FROM partida_presupuestada pp "
            "JOIN presupuesto p ON p.id = pp.presupuesto_id WHERE p.codigo = ?",
            (version,),
        ).fetchall()
    assert len(filas) == 6
    return sum((Decimal(f[0]) for f in filas), Decimal(0))


def _la_obra(s: Session) -> models.Proyecto:
    return s.scalars(select(models.Proyecto).where(models.Proyecto.nombre == OBRA)).one()


def _enviar(motor: Engine, version: str, ahora: datetime, nota: str = "", usuario: str = ANA):
    with abrir_sesion(motor) as s:
        return aprobaciones.enviar(s, OBRA, version, nota=nota, usuario=usuario, ahora=ahora)


def _dictaminar(motor: Engine, envio: int, resultado: str, notas: str, usuario: str, ahora):
    with abrir_sesion(motor) as s:
        aprobaciones.dictaminar(
            s, envio, resultado=resultado, notas=notas, usuario=usuario, ahora=ahora
        )


def _reflejar(instalacion: Session, caso: str, motor: Engine) -> None:
    with abrir_sesion(motor) as s:
        indice_aprobaciones.reflejar(instalacion, caso, s)
    instalacion.commit()


def _fila(motor: Engine, caso: str, envio_id: int, **campos) -> FilaIndice:
    """La fila esperada de VIV-001 enviada por Ana el lunes, con lo que cambie `campos`."""
    base = {
        "caso": caso,
        "envio_id": envio_id,
        "proyecto": "1",
        "obra": OBRA,
        "version": "VIV-001",
        "total": _total(motor, "VIV-001"),
        "moneda": "Bs",
        "estado": "en_aprobacion",
        "enviado_por": ANA,
        "enviado_el": LUNES,
        "dictamen_por": None,
        "dictamen_el": None,
        "nota": "",
        "notas": "",
        "armo": False,
    }
    return FilaIndice(**{**base, **campos})


def test_sin_envios_el_indice_esta_vacio(instalacion: Session, carpetas) -> None:
    _reflejar(instalacion, "a.db", carpetas["a.db"])
    assert indice_aprobaciones.pendientes(instalacion) == []
    assert indice_aprobaciones.de_quien(instalacion, ANA) == []


def test_un_envio_queda_por_aprobar_con_su_total_y_su_moneda(instalacion: Session, carpetas):
    motor = carpetas["a.db"]
    envio = _enviar(motor, "VIV-001", LUNES, nota="Primera entrega")
    _reflejar(instalacion, "a.db", motor)

    esperada = _fila(motor, "a.db", envio.id, nota="Primera entrega")
    assert indice_aprobaciones.pendientes(instalacion) == [esperada]
    assert indice_aprobaciones.de_quien(instalacion, ANA) == [esperada]
    assert indice_aprobaciones.de_quien(instalacion, "Ana María <ana>") == [esperada]
    assert indice_aprobaciones.de_quien(instalacion, RITA) == []
    assert esperada.total > 0  # seis partidas con precio


def test_el_dictamen_sale_de_por_aprobar_y_vuelve_a_quien_envio(instalacion: Session, carpetas):
    motor = carpetas["a.db"]
    envio = _enviar(motor, "VIV-001", LUNES)
    _reflejar(instalacion, "a.db", motor)
    _dictaminar(motor, envio.id, "devuelta", "Falta el acero de la losa.", RITA, MARTES)
    _reflejar(instalacion, "a.db", motor)

    assert indice_aprobaciones.pendientes(instalacion) == []
    assert indice_aprobaciones.de_quien(instalacion, ANA) == [
        _fila(
            motor,
            "a.db",
            envio.id,
            estado="devuelta",
            dictamen_por=RITA,
            dictamen_el=MARTES,
            notas="Falta el acero de la losa.",
        )
    ]


def test_quien_la_armo_y_la_aprueba_queda_rotulado(instalacion: Session, carpetas) -> None:
    motor = carpetas["a.db"]
    envio = _enviar(motor, "VIV-001", LUNES)
    _dictaminar(motor, envio.id, "aprobada", "", ANA, MARTES)
    _reflejar(instalacion, "a.db", motor)
    (fila,) = indice_aprobaciones.de_quien(instalacion, ANA)
    assert (fila.estado, fila.dictamen_por, fila.armo) == ("aprobada", ANA, True)


def test_la_retirada_queda_retirada_sin_dictamen(instalacion: Session, carpetas) -> None:
    motor = carpetas["a.db"]
    with abrir_sesion(motor) as s:
        guardar_version(s, _la_obra(s), "VIV-002", cantidades={"OBRA-01": "90"})
    primero = _enviar(motor, "VIV-001", LUNES)
    segundo = _enviar(motor, "VIV-002", MARTES)
    _reflejar(instalacion, "a.db", motor)
    assert indice_aprobaciones.de_quien(instalacion, ANA) == [
        _fila(
            motor,
            "a.db",
            segundo.id,
            version="VIV-002",
            total=_total(motor, "VIV-002"),
            enviado_el=MARTES,
        ),
        _fila(motor, "a.db", primero.id, estado="retirada"),
    ]
    assert _total(motor, "VIV-002") != _total(motor, "VIV-001")


def test_por_aprobar_junta_todas_las_carpetas_la_mas_antigua_primero(
    instalacion: Session, carpetas
) -> None:
    a, b = carpetas["a.db"], carpetas["b.db"]
    en_b = _enviar(b, "VIV-001", LUNES)
    en_a = _enviar(a, "VIV-001", MIERCOLES)
    _reflejar(instalacion, "a.db", a)
    _reflejar(instalacion, "b.db", b)
    assert [(f.caso, f.envio_id) for f in indice_aprobaciones.pendientes(instalacion)] == [
        ("b.db", en_b.id),
        ("a.db", en_a.id),
    ]


def test_reflejar_reescribe_solo_las_filas_de_esa_carpeta(instalacion: Session, carpetas):
    a, b = carpetas["a.db"], carpetas["b.db"]
    en_a = _enviar(a, "VIV-001", LUNES)
    en_b = _enviar(b, "VIV-001", MARTES)
    _reflejar(instalacion, "a.db", a)
    _reflejar(instalacion, "b.db", b)
    # una fila vieja de «a.db» que su carpeta ya no tiene, y la fila real borrada a mano
    instalacion.execute(text("DELETE FROM mp_indice_aprobacion WHERE caso = 'a.db'"))
    instalacion.execute(
        text(
            "INSERT INTO mp_indice_aprobacion (caso, envio_id, proyecto, obra, version, total, "
            "moneda, estado, enviado_por, enviado_el, nota, notas, armo) VALUES ('a.db', 99, '1', "
            "'Obra vieja', 'X-1', '1', 'Bs', 'en_aprobacion', 'Ana <ana>', "
            "'2026-10-01 08:00:00.000000', '', '', 0)"
        )
    )
    instalacion.commit()

    _reflejar(instalacion, "a.db", a)

    assert [(f.caso, f.envio_id) for f in indice_aprobaciones.pendientes(instalacion)] == [
        ("a.db", en_a.id),
        ("b.db", en_b.id),
    ]


def test_mias_trae_las_mas_recientes_hasta_el_limite(instalacion: Session, carpetas) -> None:
    motor = carpetas["a.db"]
    with abrir_sesion(motor) as s:
        obra = _la_obra(s)
        guardar_version(s, obra, "VIV-002", cantidades={"OBRA-01": "90"})
        guardar_version(s, obra, "VIV-003", cantidades={"OBRA-01": "95"})
    _enviar(motor, "VIV-001", LUNES)
    _enviar(motor, "VIV-002", MARTES)
    _enviar(motor, "VIV-003", JUEVES)
    _reflejar(instalacion, "a.db", motor)
    assert [f.version for f in indice_aprobaciones.de_quien(instalacion, ANA, limite=2)] == [
        "VIV-003",
        "VIV-002",
    ]
    assert len(indice_aprobaciones.de_quien(instalacion, ANA)) == 3
