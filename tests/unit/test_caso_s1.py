"""El caso S1 de la base de prueba de la 0.6.0 (RV-3, PRU-H15): lo que `plantilla_s1` siembra."""

from decimal import Decimal as D  # noqa: N817

from sqlalchemy import select

from core import models
from core.budget.moneda import moneda_del_proyecto
from core.budget.reajuste import cargar_estudio
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.caso_s1 import plantilla_s1


def test_la_plantilla_s1_trae_la_clinica_convertida_la_lista_de_empresa_y_el_estudio(tmp_path):
    ruta = tmp_path / "s1.db"
    preparar_base(ruta)
    plantilla_s1(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            motivos = sesion.scalars(select(models.VersionOrigen.motivo)).all()
            assert "conversion" in motivos
            assert sesion.scalars(select(models.ListaEmpresa)).all()
            estudio = sesion.scalars(select(models.EstudioReajuste)).one()
            assert cargar_estudio(sesion, estudio.id).resultado.total_escalatoria == D("15300")
            proyectos = sesion.scalars(select(models.Proyecto)).all()
            assert {moneda_del_proyecto(sesion, p) for p in proyectos} >= {"Bs"}
    finally:
        motor.dispose()
