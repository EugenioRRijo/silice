from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from core import models
from core.catalog import Catalogo
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from tests.fixtures.versiones import elaborar_001, guardar_001
from ui import hoja


@pytest.fixture
def clinica(sesion):
    proyecto = sesion.scalars(select(models.Proyecto)).one()
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    registrar_importacion(sesion, definicion_tasa("venta"), [Observacion(date(2026, 10, 1),
                          Decimal("860.18"))], archivo="FUENTE.md", huella="d" * 64,
                          fuente="https://www.bcv.org.ve/", fecha_descarga=date(2026, 10, 8),
                          responsable="A", filas_leidas=1, filas_rechazadas=0)
    sesion.commit()
    return sesion, proyecto.nombre


def test_convertir_desde_la_hoja_abre_la_version_en_bs_y_hereda_el_espacio(clinica):
    sesion, nombre = clinica
    nuevo = hoja.convertir(sesion, Catalogo(sesion), nombre, "001", "Bs", lado="venta",
                           fecha=date(2026, 10, 3), fuente="cambio", responsable="Ing.")
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), nombre, nuevo)
    assert abierta.borrador.moneda == "Bs"
    assert "conversion" in hoja.MOTIVOS_QUE_HEREDAN_EL_ESPACIO


def test_sin_tasa_en_7_dias_la_hoja_lo_dice_y_no_escribe(clinica):
    sesion, nombre = clinica
    with pytest.raises(hoja.HojaInvalida, match="7 dias"):
        hoja.convertir(sesion, Catalogo(sesion), nombre, "001", "Bs", lado="venta",
                       fecha=date(2026, 10, 12), fuente="cambio", responsable="Ing.")


def test_precios_muestran_seis_datos_erosion_26_37_y_estado_r12(clinica):
    sesion, nombre = clinica
    filas = hoja.precios_de_version(sesion, nombre, "001", fecha_evaluacion=date(2026, 10, 1))
    assert all(f.moneda_original == "USD" and f.fuente for f in filas)
    assert all("R12 ADVERTENCIA" in f.estado for f in filas)  # precios del 28/04/2026, vencidos
    assert all(f.erosion_bs == Decimal(0) for f in filas)  # originales en USD: erosión 0 declarada


def test_abrir_con_fecha_reaudita_en_memoria_sin_tocar_los_guardados(clinica):
    sesion, nombre = clinica
    sin = hoja.abrir_version(sesion, Catalogo(sesion), nombre, "001")
    con = hoja.abrir_version(sesion, Catalogo(sesion), nombre, "001",
                             fecha_evaluacion=date(2026, 10, 1))
    assert not [h for h in sin.guardada.informe.hallazgos if h.regla in ("R11", "R12")]
    assert [h for h in con.guardada.informe.hallazgos if h.regla == "R12"]
    assert not sesion.scalars(select(models.Hallazgo).where(models.Hallazgo.regla == "R12")).all()
