"""RF-68: conjunto EXACTO de tests/fixtures/memorias/s1_precios_empresa.md a 2026-10-01."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from core import models
from core.budget.instantanea import instantanea_precios
from core.catalog.empresa import instantanea_de_lista
from core.contracts import Severidad
from core.verification.precios import reglas_precios
from tests.fixtures.precios_empresa_s1 import EVALUACION, sembrar

A, INF, E = Severidad.ADVERTENCIA, Severidad.INFO, Severidad.ERROR
ESPERADO = {  # (regla, severidad, insumo) -> impacto en la versión a ± 0,01 (None: sin impacto)
    ("R11", A, 'UNION PVC A.B. 4"'): Decimal("13377.74"),
    ("R11", A, "ARENA LAVADA"): Decimal("143309.00"),
    ("R11", INF, "LIJA DE AGUA N 100"): None,
    ("R12", A, 'CLAVO DE ACERO LISO L=2 1/2"'): Decimal("1368.10"),
    ("R12", A, "MATERIAL GRANULAR INTEGRAL"): Decimal("20521.45"),
    ("R12", E, "PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM"): None,
    ("R12", A, 'TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA'): Decimal("0.00"),
}


def _hallazgos(inst):
    return [h for regla in reglas_precios(inst) for h in regla.evaluar(None)]


def _clave(h):
    insumo = next(d for (_, _, d) in ESPERADO if d.upper() in h.descripcion.upper())
    return (h.regla, h.severidad, insumo)


def test_conjunto_exacto_de_la_memoria(sesion):
    referencia, _, version = sembrar(sesion)
    hallazgos = _hallazgos(instantanea_precios(sesion, version, referencia, EVALUACION))
    assert len(hallazgos) == len(ESPERADO)
    for h in hallazgos:
        esperado = ESPERADO[_clave(h)]
        assert (h.impacto is None) == (esperado is None)
        if esperado is not None:
            assert (h.impacto - esperado).copy_abs() <= Decimal("0.01")
        assert h.origen_ids in ((), ("S1-EMP-01",))
    assert next(
        h for h in hallazgos if "UNION" in h.descripcion.upper()
    ).valor_observado == Decimal("-0.2001")


def test_por_lista_el_impacto_es_por_unidad(sesion):
    referencia, lista, _ = sembrar(sesion)
    arena = next(
        h
        for h in _hallazgos(instantanea_de_lista(sesion, lista, referencia, EVALUACION))
        if "ARENA" in h.descripcion.upper()
    )
    assert (arena.impacto - Decimal("11328.78")).copy_abs() <= Decimal("0.01")


def test_reevaluar_a_otra_fecha_cambia_lo_mostrado_y_no_las_filas(sesion):
    referencia, _, version = sembrar(sesion)
    guardadas = sesion.scalars(
        select(models.Hallazgo).where(models.Hallazgo.presupuesto_id == version.id)
    ).all()
    antes = [(h.regla, h.descripcion, h.impacto) for h in guardadas]
    otra = _hallazgos(instantanea_precios(sesion, version, referencia, date(2026, 10, 6)))
    assert any("AGUA" in h.descripcion.upper() and h.regla == "R12" for h in otra)  # 35 días
    assert [
        (h.regla, h.descripcion, h.impacto)
        for h in sesion.scalars(
            select(models.Hallazgo).where(models.Hallazgo.presupuesto_id == version.id)
        )
    ] == antes
