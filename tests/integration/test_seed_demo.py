"""Una sola orden deja la aplicacion lista (Tarea 2, sesion P4.2, primera mitad).

Reproduce y cierra los hechos verificados 8 y 9 del encabezado del plan
(`.superpowers/sdd/2026-09-21-prototipo-arenia-fases-p4-p5/task-2-brief.md`):

8. `scripts/seed_demo.py` creaba su lista de precios vacia, sin heredar los precios de la vigente.
   Sembrar la linea base y despues la demostracion en la misma base dejaba las cinco partidas
   `LB-*` sin precio desde la fecha de la lista de la demostracion en adelante.
9. Ninguna partida sembrada tenia dos observaciones de rendimiento, asi que la advertencia RF-27
   no se podia ejercitar contra la base sembrada.

Todas las pruebas trabajan contra `tmp_path`: nunca contra `data/apu.db` (restriccion global del
plan). Cada prueba que abre un motor SQLAlchemy lo cierra siempre con `motor.dispose()` (en
Windows, un archivo abierto impide borrar el temporal).

Ningun total se transcribe: el total del presupuesto de ejemplo se compara contra
`scripts.seed_demo.elaborar_caso_demo`, no contra un numero copiado a mano (una prueba que
transcribiera el total dejaria de ser una regresion en cuanto alguien corrigiera el caso).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from core import models
from core.budget import cargar_presupuesto
from core.catalog import (
    MINIMO_OBSERVADO_PARA_ADVERTIR,
    Catalogo,
    abrir_sesion,
    advertencia_rendimiento,
    crear_motor,
    dispersion_rendimientos,
    proponer_rendimiento,
)
from core.costing import calcular_apu
from scripts import seed, seed_demo
from tests.fixtures import apu_linea_base as linea_base

#: Los tres codigos del caso de demostracion: se repiten en varias pruebas de este archivo.
CODIGOS_DEMO = ("DEMO-01-INST", "DEMO-02-VALV", "DEMO-03-PRUEBA")

_TABLAS_IDEMPOTENCIA = (
    models.Partida,
    models.ListaPrecios,
    models.Presupuesto,
    models.PrecioInsumo,
    models.Rendimiento,
)


def _assert_linea_base_y_demo_valorables(catalogo: Catalogo, fecha: date | None = None) -> None:
    """Los cinco APU de la linea base valen lo mismo reconstruidos, y las tres DEMO no fallan."""
    for apu in linea_base.APUS_LINEA_BASE:
        reconstruido = catalogo.composicion(apu.codigo_partida, fecha=fecha)
        esperado = calcular_apu(apu, linea_base.PARAMETROS_LINEA_BASE)
        obtenido = calcular_apu(reconstruido, linea_base.PARAMETROS_LINEA_BASE)
        assert obtenido.precio_unitario == esperado.precio_unitario, apu.codigo_partida

    for codigo in CODIGOS_DEMO:
        catalogo.composicion(codigo, fecha=fecha)  # no debe lanzar CatalogoIncompleto


def _contar_tablas(base: Path) -> tuple[int, ...]:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return tuple(
                sesion.scalar(select(func.count()).select_from(tabla))
                for tabla in _TABLAS_IDEMPOTENCIA
            )
    finally:
        motor.dispose()


def test_una_sola_orden_deja_linea_base_y_demo_valorables_hoy(tmp_path: Path) -> None:
    """`seed_demo.main` solo: la linea base y la demostracion quedan valorables hoy mismo.

    Hoy falla: `sembrar_demo` nunca siembra la linea base, asi que `Catalogo.composicion` de
    cualquier `LB-*` lanza `KeyError` (la partida no existe en el catalogo).
    """
    base = tmp_path / "una_orden.db"
    assert seed_demo.main(["--db", str(base)]) == 0

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            _assert_linea_base_y_demo_valorables(Catalogo(sesion), fecha=date.today())
    finally:
        motor.dispose()


def test_sembrar_la_demo_sobre_una_base_con_linea_base_no_la_rompe(tmp_path: Path) -> None:
    """El escenario de quien ya tiene `data/apu.db` con la linea base y siembra la demo encima.

    Hoy falla con `CatalogoIncompleto`: la lista de precios de la demostracion nace vacia y pasa a
    ser la vigente desde `FECHA_DEMO`, asi que ningun `LB-*` tiene precio desde esa fecha.
    """
    base = tmp_path / "linea_base_primero.db"
    assert seed.main(["--db", str(base)]) == 0
    assert seed_demo.main(["--db", str(base)]) == 0

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            _assert_linea_base_y_demo_valorables(Catalogo(sesion), fecha=date.today())
    finally:
        motor.dispose()


def test_deja_guardado_el_presupuesto_de_ejemplo(tmp_path: Path) -> None:
    """El presupuesto `DEMO-001` queda guardado con el mismo total que produce el caso elaborado.

    Hoy falla: `main` no guarda ningun presupuesto (no existe `guardar_presupuesto_demo`), asi que
    `cargar_presupuesto` no encuentra nada que cargar.
    """
    base = tmp_path / "presupuesto.db"
    assert seed_demo.main(["--db", str(base)]) == 0

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            presupuesto = cargar_presupuesto(
                sesion, seed_demo.NOMBRE_PROYECTO, seed_demo.CODIGO_PRESUPUESTO, catalogo
            )
    finally:
        motor.dispose()

    esperado = seed_demo.elaborar_caso_demo(seed_demo.construir_caso_demo())

    assert presupuesto.total == esperado.presupuesto.total


def test_demo_01_tiene_historial_para_la_advertencia_de_rendimiento(tmp_path: Path) -> None:
    """`DEMO-01-INST` acumula suficientes observaciones para que RF-27 tenga algo que advertir.

    Hoy falla: ninguna partida sembrada tiene dos observaciones de rendimiento (hecho verificado
    9), asi que `dispersion_rendimientos` no llega al minimo que exige `advertencia_rendimiento`.
    """
    base = tmp_path / "rendimiento.db"
    assert seed_demo.main(["--db", str(base)]) == 0

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            dispersion = dispersion_rendimientos(sesion, "DEMO-01-INST")
            assert dispersion is not None
            assert dispersion.observaciones >= MINIMO_OBSERVADO_PARA_ADVERTIR

            assert advertencia_rendimiento(dispersion, dispersion.maximo * 2) is not None
            assert advertencia_rendimiento(dispersion, dispersion.minimo) is None

            propuesta = proponer_rendimiento(sesion, "DEMO-01-INST")
            assert propuesta is not None

            composicion_caso = next(
                apu
                for apu in seed_demo.construir_caso_demo().composiciones
                if apu.codigo_partida == "DEMO-01-INST"
            )
            assert propuesta.rendimiento.valor == composicion_caso.rendimiento
    finally:
        motor.dispose()


def test_es_idempotente(tmp_path: Path) -> None:
    """`main` dos veces sobre la misma base no cambia ningun recuento."""
    base = tmp_path / "idempotente.db"

    assert seed_demo.main(["--db", str(base)]) == 0
    conteos_primera_vez = _contar_tablas(base)

    assert seed_demo.main(["--db", str(base)]) == 0
    conteos_segunda_vez = _contar_tablas(base)

    assert conteos_primera_vez == conteos_segunda_vez
