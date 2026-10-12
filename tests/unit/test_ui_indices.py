from datetime import date

from sqlalchemy import func, select

from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from tests.fixtures.bcv_cuadriculas import CARPETA, campo
from ui import indices


def test_leer_no_escribe_y_confirmar_es_idempotente(tmp_path):
    ruta = CARPETA / campo("Tasa", "Archivo")
    informe = indices.leer(ruta, "tasa", fuente=campo("Tasa", "Dirección"),
                           fecha_descarga=date.fromisoformat(campo("Tasa", "Fecha de descarga")))
    motor = crear_motor(f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        assert sesion.scalar(select(func.count()).select_from(models.ValorIndice)) == 0
        primero = indices.confirmar(sesion, informe, responsable="Admin")
        segundo = indices.confirmar(sesion, informe, responsable="Admin")
        assert all("importada" in m for m in primero) and all("ya importado" in m for m in segundo)
    motor.dispose()
