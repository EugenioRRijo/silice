"""El caso S2 que alimenta la base de prueba de la 0.7.0: se siembra en una base nueva en `head` y
da lo que dice la memoria `control_ob_s2.md` (PRU-H15)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from core import models
from core.budget.decision import decisiones
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures.caso_s2 import MOMENTO_DE_LA_DECISION, plantilla_s2

D = Decimal


def test_la_plantilla_s2_siembra_la_obra_sus_valuaciones_y_su_decision(tmp_path: Path) -> None:
    ruta = tmp_path / "s2.db"
    preparar_base(ruta)
    plantilla_s2(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            numeros = sesion.scalars(select(models.Valuacion.numero).order_by(models.Valuacion.id))
            assert list(numeros) == ["V-01", "V-02"]
            codigos = sesion.scalars(
                select(models.Presupuesto.codigo).order_by(models.Presupuesto.id)
            )
            assert list(codigos) == ["OB-001", "OB-002"]
            (decision,) = decisiones(sesion, "OB-S2")
            assert (decision.opcion, decision.termino.isoformat()) == ("cuadrillas", "2026-11-24")
            assert decision.costo_directo_adicional == D(120)
            assert decision.fecha_hora == MOMENTO_DE_LA_DECISION  # la base se reconstruye igual
            assert decision.fecha_corte.isoformat() == "2026-11-13"  # corte de la memoria §2
            assert decision.spi == D("0.8") and decision.cpi == D("0.9375")  # memoria §3
            registros = sesion.scalars(
                select(models.RegistroCambio).where(models.RegistroCambio.objeto == "plan")
            ).all()
            assert len(registros) == 7
    finally:
        motor.dispose()
