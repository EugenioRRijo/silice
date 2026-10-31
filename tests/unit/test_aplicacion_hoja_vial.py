"""Plan vial, Tarea 10: las reglas viales VR1 a VR7 entran a la auditoria de la Hoja. FICTICIO.

`aplicacion.hoja.abrir_version` las suma a `reglas_extra` junto a R11 y R12: se evaluan al abrir,
en memoria; ninguna fila guardada cambia. Via de prueba: T1, 0 a 1 km, 7 m de ancho, carpeta de
0,05 m a 2,4 t/m3, transporte desde 10 km. Oraculo a mano: mezcla 7.000 x 0,05 x 2,4 = 840 t.
La version `VIAL-001` guarda 900 t en la carpeta (con `origen_id` «tramo:T1:capa:1»): VR1 la marca;
con 840 t no hay ningun VR. `VIV-001` (sin tramos) no muestra ninguno.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Tramo
from adapters.vial.reglas import ReglasViales
from aplicacion import hoja, hoja_vista, vial
from aplicacion.hoja_borradores import Registro
from core import models
from core.budget import elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import Dominio, OrigenTipo
from core.contracts.apu import ComposicionAPU, LineaMaterial
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import (
    FECHA,
    OBRA,
    PARAMETROS,
    sembrar_vivienda,
)

D = Decimal
ANA = "Ana <ana>"
LUNES = datetime(2026, 10, 19, 9, 0)
HOY = date(2026, 10, 31)
CAPA1 = "tramo:T1:capa:1"
T1 = Tramo("T1", D("0"), D("1"), D("7"), (Capa("carpeta", D("0.05"), D("2.4"), None),), (), D("10"))
MEZCLA = PARTIDAS_VIALES["carpeta_mezcla"][0]
PRECIOS = {"carpeta": "10", "carpeta_mezcla": "200", "transporte_mezcla": "2"}


def _composiciones() -> dict[str, ComposicionAPU]:
    resultado = {}
    for clave, precio in PRECIOS.items():
        codigo, descripcion, unidad = PARTIDAS_VIALES[clave]
        linea = LineaMaterial(f"Material de {codigo}", unidad, D("1"), D(precio))
        resultado[codigo] = ComposicionAPU(
            codigo, descripcion, unidad, D("10"), materiales=(linea,)
        )
    return resultado


def _catalogar(sesion: Session) -> None:
    """Las tres partidas viales en el catalogo (la Hoja las necesita para abrir la version)."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "Lista Bs de prueba")
    ).one()
    for composicion in _composiciones().values():
        Catalogo(sesion).cargar_composicion(composicion, lista, Dominio.CIVIL, FECHA, "prueba")


def _guardar_vial(
    sesion: Session, obra: models.Proyecto, toneladas: str, codigo: str = "VIAL-001"
) -> models.Presupuesto:
    """La version `codigo`: las tres partidas de la via; las toneladas de la carpeta, las que se
    indiquen (a mano: sin regla, para que R1 no mezcle su aviso con el de VR1)."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "Lista Bs de prueba")
    ).one()
    composiciones = _composiciones()
    items = [
        replace(i, cantidad=D(toneladas), regla=None, parametros={}, origen_tipo=OrigenTipo.TABULAR)
        if i.codigo_partida == MEZCLA
        else i
        for i in derivar_tramos([T1])
    ]
    resultado = elaborar(
        items,
        composiciones,
        PARAMETROS,
        codigo=codigo,
        fecha=FECHA,
        moneda="Bs",
        plan=plan_secuencial,
    )
    version = guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=obra,
        lista=lista,
        parametros=PARAMETROS,
        pendientes=resultado.pendientes,
        usuario=ANA,
    )
    sesion.commit()
    return version


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[tuple[Engine, Session]]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            obra = sembrar_vivienda(sesion, usuario=ANA)
            _catalogar(sesion)
            _guardar_vial(sesion, obra, "900")
            yield motor, sesion
    finally:
        motor.dispose()


def _version_id(sesion: Session, codigo: str) -> int:
    return sesion.scalars(
        select(models.Presupuesto.id).where(models.Presupuesto.codigo == codigo)
    ).one()


def _reglas(abierta: hoja.VersionAbierta) -> list[str]:
    return [h.regla for h in abierta.guardada.informe.hallazgos]


def _filas(motor: Engine) -> dict[str, int]:
    """Las filas de cada tabla de la carpeta, salvo las del anexo vial."""
    with closing(sqlite3.connect(motor.url.database)) as conexion:
        tablas = [
            n
            for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            if not n.startswith(("vial_", "sqlite_"))
        ]
        return {t: conexion.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tablas}


def test_una_version_con_tramos_y_la_carpeta_alterada_muestra_su_vr1(caso):
    _, sesion = caso
    vial.guardar_tramos(sesion, _version_id(sesion, "VIAL-001"), [T1], usuario=ANA, ahora=LUNES)
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, "VIAL-001", fecha_evaluacion=HOY)
    vr = [h for h in abierta.guardada.informe.hallazgos if h.regla.startswith("VR")]
    assert [(h.regla, h.origen_ids, h.valor_observado, h.valor_esperado) for h in vr] == [
        ("VR1", (CAPA1,), D("900"), D("840"))
    ]
    assert sum(isinstance(r, ReglasViales) for r in abierta.borrador.reglas_extra) == 1
    # y en la vista de hallazgos de la Hoja (la pestana Auditoria)
    vivo = Registro().crear("f", "caso", OBRA, "VIAL-001", abierta.borrador, abierta)
    en_vista = [h for h in hoja_vista.informe_de_auditoria(vivo).hallazgos if h.regla == "VR1"]
    assert [h.origen_ids for h in en_vista] == [(CAPA1,)]
    assert "900 t" in en_vista[0].descripcion and "840 t" in en_vista[0].descripcion


def test_sin_fecha_de_evaluacion_tambien_se_evaluan(caso):
    _, sesion = caso
    vial.guardar_tramos(sesion, _version_id(sesion, "VIAL-001"), [T1], usuario=ANA, ahora=LUNES)
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, "VIAL-001")
    assert "VR1" in _reglas(abierta)


def test_una_version_sin_tramos_no_muestra_ningun_vr(caso):
    _, sesion = caso
    for codigo in ("VIV-001", "VIAL-001"):
        abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, codigo, fecha_evaluacion=HOY)
        assert not [r for r in _reglas(abierta) if r.startswith("VR")]
        assert not [r for r in abierta.borrador.reglas_extra if isinstance(r, ReglasViales)]


def test_con_tramos_y_la_carpeta_coherente_no_hay_vr(tmp_path):
    ruta = tmp_path / "coherente.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            obra = sembrar_vivienda(sesion, usuario=ANA)
            _catalogar(sesion)
            version = _guardar_vial(sesion, obra, "840")
            vial.guardar_tramos(sesion, version.id, [T1], usuario=ANA, ahora=LUNES)
            abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, "VIAL-001")
            assert not [r for r in _reglas(abierta) if r.startswith("VR")]
            assert sum(isinstance(r, ReglasViales) for r in abierta.borrador.reglas_extra) == 1
    finally:
        motor.dispose()


def test_una_version_posterior_hereda_los_tramos_y_muestra_su_vr1(caso):
    _, sesion = caso
    vial.guardar_tramos(sesion, _version_id(sesion, "VIAL-001"), [T1], usuario=ANA, ahora=LUNES)
    obra = sesion.scalars(select(models.Proyecto)).one()
    nueva = _guardar_vial(sesion, obra, "900", "VIAL-002")
    assert vial.heredados_de(sesion, nueva.id) == "VIAL-001"
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, nueva.codigo)
    assert "VR1" in _reglas(abierta)


def test_abrir_no_cambia_ninguna_fila_guardada(caso):
    motor, sesion = caso
    hoja.abrir_version(sesion, Catalogo(sesion), OBRA, "VIAL-001", fecha_evaluacion=HOY)
    antes = _filas(motor)  # ya con la instantanea que abrir congela la primera vez
    vial.guardar_tramos(sesion, _version_id(sesion, "VIAL-001"), [T1], usuario=ANA, ahora=LUNES)
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), OBRA, "VIAL-001", fecha_evaluacion=HOY)
    assert "VR1" in _reglas(abierta)
    assert _filas(motor) == antes
