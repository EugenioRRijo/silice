"""RF-64, RF-65 (S1 §9.2). Oráculo independiente: homogeneidad del PU (total × T)."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import actualizar_precios, cargar_presupuesto, plan_de_version, restaurar_version
from core.budget.moneda import convertir_version, moneda_del_proyecto
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.catalog.moneda import TasaDeclarada
from tests.fixtures.base_con_pendiente import url_sqlite
from tests.fixtures.hoja_en_base import NOMBRE_TI001, plantilla_ti001
from tests.fixtures.versiones import elaborar_001, guardar_001

D = Decimal

TASA = TasaDeclarada(D("860.18"), date(2026, 10, 1), "importacion:1")
CENT = D("0.01")


@pytest.fixture
def clinica(sesion):
    proyecto = sesion.scalars(select(models.Proyecto)).one()
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    sesion.flush()
    return sesion, proyecto.nombre


def _convertir(sesion, nombre, codigo="001", nuevo="002", moneda="Bs", tasa=TASA):
    return convertir_version(sesion, nombre, codigo, nuevo, moneda, tasa, fuente="cambio pedido",
                             responsable="Ing. Prueba", catalogo=Catalogo(sesion))


def _total(sesion, nombre, codigo):
    return cargar_presupuesto(sesion, nombre, codigo, Catalogo(sesion)).total


def test_la_clinica_en_bs_es_el_total_por_la_tasa_y_el_origen_no_cambia(clinica):
    sesion, nombre = clinica
    antes = cargar_presupuesto(sesion, nombre, "001", Catalogo(sesion))
    nueva = _convertir(sesion, nombre)
    assert (_total(sesion, nombre, "002") - antes.total * TASA.valor).copy_abs() <= CENT
    assert nueva.moneda == "Bs" and nueva.bono_alimentacion == D("860.18")
    assert nueva.lista_precios.moneda == "Bs"
    origen = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == "001")
    ).one()
    assert plan_de_version(sesion, nueva) == plan_de_version(sesion, origen)
    assert not [h for h in nueva.hallazgos if h.regla == "R2"]
    assert cargar_presupuesto(sesion, nombre, "001", Catalogo(sesion)) == antes


def test_registra_moneda_del_proyecto_y_registro_de_cambio(clinica):
    sesion, nombre = clinica
    nueva = _convertir(sesion, nombre)
    registro = sesion.scalars(select(models.RegistroCambio).where(
        models.RegistroCambio.version_resultante_id == nueva.id)).one()
    assert (registro.objeto, registro.valor_anterior, registro.valor_nuevo, registro.fuente) == (
        "moneda", "USD", "Bs", "importacion:1")
    assert moneda_del_proyecto(sesion, nueva.proyecto) == "Bs"
    assert sesion.get(models.VersionOrigen, nueva.id).motivo == "conversion"


def test_ida_y_vuelta_y_ti001(clinica, tmp_path):
    sesion, nombre = clinica
    original = _total(sesion, nombre, "001")
    _convertir(sesion, nombre)
    _convertir(sesion, nombre, "002", "003", "USD")
    assert (_total(sesion, nombre, "003") - original).copy_abs() <= CENT
    motor = crear_motor(url_sqlite(plantilla_ti001(tmp_path / "ti.db")))
    try:
        with abrir_sesion(motor) as otra:
            antes = _total(otra, NOMBRE_TI001, "TI-001")
            _convertir(otra, NOMBRE_TI001, "TI-001", "TI-002")
            assert (_total(otra, NOMBRE_TI001, "TI-002") - antes * TASA.valor).copy_abs() <= CENT
    finally:
        motor.dispose()


def test_lista_de_otra_moneda_se_rechaza_al_guardar_y_al_revalorar(clinica):
    sesion, nombre = clinica
    lista_bs = models.ListaPrecios(nombre="Bs", moneda="Bs", fecha_vigencia=date(2026, 5, 1))
    sesion.add(lista_bs)
    sesion.flush()
    with pytest.raises(ValueError, match="RF-65"):
        guardar_001(sesion, sesion.scalars(select(models.Proyecto)).one(),
                    replace(elaborar_001(sesion, codigo="009")), lista=lista_bs)
    antes = sesion.scalar(select(func.count()).select_from(models.CambioPrecio))
    with pytest.raises(ValueError, match="RF-65"):
        actualizar_precios(sesion, nombre, "001", lista_bs, "010")
    assert sesion.scalar(select(func.count()).select_from(models.CambioPrecio)) == antes


def test_moneda_cambiada_con_versiones_previas_no_se_restauran_en_la_vieja(clinica):
    """[Foco 3] tras convertir a Bs, restaurar o revalorar la 001 en USD se rechaza."""
    sesion, nombre = clinica
    _convertir(sesion, nombre)
    with pytest.raises(ValueError, match="convierta"):
        restaurar_version(sesion, nombre, "001", "004", Catalogo(sesion), fuente="x",
                          responsable="y")


def test_tasa_incompleta_se_rechaza_sin_escribir(clinica):
    sesion, nombre = clinica
    with pytest.raises(ValueError):
        _convertir(sesion, nombre, tasa=replace(TASA, fuente=""))
    assert sesion.scalar(select(func.count()).select_from(models.MonedaProyecto)) == 0
