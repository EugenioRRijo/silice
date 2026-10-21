"""Proyectos del caso abierto (RF-63, spec §9.7): crear con nombre unico y no vacio, listar, version
vigente y resumen de auditoria. `aplicacion.proyectos` no importa Streamlit: se prueba como
funcion pura sobre una base en `tmp_path`.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import hoja, proyectos
from aplicacion.proyectos import ProyectoInvalido
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import Severidad
from scripts.seed import NOMBRE_PROYECTO
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.base_con_pendiente import guardar_base_con_pendiente


@pytest.fixture
def base(tmp_path: Path):
    ruta = tmp_path / "caso.db"
    resultado = guardar_base_con_pendiente(ruta)
    return ruta, resultado


def test_listar_devuelve_los_proyectos_en_orden_alfabetico(base):
    ruta, _ = base
    assert proyectos.listar_proyectos(ruta) == [NOMBRE_PROYECTO]
    proyectos.crear_proyecto_nuevo(ruta, "Anexo norte")
    assert proyectos.listar_proyectos(ruta) == ["Anexo norte", NOMBRE_PROYECTO]


def test_listar_sin_archivo_no_lo_crea(tmp_path):
    ruta = tmp_path / "no_existe.db"
    assert proyectos.listar_proyectos(ruta) == []
    assert not ruta.exists()


def test_crear_devuelve_el_nombre_sin_espacios_sobrantes(base):
    ruta, _ = base
    assert proyectos.crear_proyecto_nuevo(ruta, "  Torre B  ") == "Torre B"
    assert "Torre B" in proyectos.listar_proyectos(ruta)


@pytest.mark.parametrize("nombre", ["", "   ", "\t\n"])
def test_nombre_vacio_se_rechaza_con_mensaje(base, nombre):
    ruta, _ = base
    antes = proyectos.listar_proyectos(ruta)
    with pytest.raises(ProyectoInvalido, match="no puede quedar vacio"):
        proyectos.crear_proyecto_nuevo(ruta, nombre)
    assert proyectos.listar_proyectos(ruta) == antes


@pytest.mark.parametrize(
    "nombre", [NOMBRE_PROYECTO, f"  {NOMBRE_PROYECTO} ", NOMBRE_PROYECTO.upper()]
)
def test_nombre_repetido_se_rechaza_aunque_cambien_espacios_o_mayusculas(base, nombre):
    ruta, _ = base
    with pytest.raises(ProyectoInvalido, match="Ya existe"):
        proyectos.crear_proyecto_nuevo(ruta, nombre)
    assert proyectos.listar_proyectos(ruta) == [NOMBRE_PROYECTO]


def test_crear_en_un_caso_que_no_existe_lo_dice_y_no_crea_el_archivo(tmp_path):
    ruta = tmp_path / "no_existe.db"
    with pytest.raises(ProyectoInvalido, match="no existe"):
        proyectos.crear_proyecto_nuevo(ruta, "Torre B")
    assert not ruta.exists()


def test_version_vigente_es_la_ultima_guardada(base):
    ruta, _ = base
    version = proyectos.version_vigente(ruta, NOMBRE_PROYECTO)
    assert version is not None
    assert version.codigo == linea_base.CODIGO_PRESUPUESTO
    assert version.fecha == linea_base.FECHA_LINEA_BASE


def test_un_proyecto_nuevo_no_tiene_version_vigente(base):
    ruta, _ = base
    proyectos.crear_proyecto_nuevo(ruta, "Torre B")
    assert proyectos.version_vigente(ruta, "Torre B") is None
    assert proyectos.resumen_auditoria(ruta, "Torre B") is None


def test_version_de_un_proyecto_desconocido_es_none(base):
    ruta, _ = base
    assert proyectos.version_vigente(ruta, "Fantasma") is None


def test_resumen_de_auditoria_coincide_con_el_informe_emitido(base):
    ruta, resultado = base
    esperado = Counter(h.severidad.name for h in resultado.informe.hallazgos)
    resumen = proyectos.resumen_auditoria(ruta, NOMBRE_PROYECTO)
    assert resumen is not None
    assert resumen.version.codigo == linea_base.CODIGO_PRESUPUESTO
    assert resumen.total == len(resultado.informe.hallazgos)
    for severidad in Severidad:
        assert resumen.por_severidad[severidad.name] == esperado.get(severidad.name, 0)
    assert resumen.total >= 1  # la base lleva un pendiente: el informe no esta vacio


def test_crear_normaliza_los_espacios_interiores(base):
    ruta, _ = base
    assert proyectos.crear_proyecto_nuevo(ruta, "  Torre   B	 norte ") == "Torre B norte"
    assert "Torre B norte" in proyectos.listar_proyectos(ruta)


def test_el_nombre_normalizado_se_compara_sin_distinguir_mayusculas(base):
    ruta, _ = base
    proyectos.crear_proyecto_nuevo(ruta, "Torre B")
    with pytest.raises(ProyectoInvalido, match="Ya existe"):
        proyectos.crear_proyecto_nuevo(ruta, "TORRE    b")
    assert proyectos.listar_proyectos(ruta).count("Torre B") == 1


# `from core import models`, `from core.catalog import Catalogo, abrir_sesion, crear_motor` y
# `from ui import hoja`; al final:
def test_proyecto_nuevo_con_moneda_declara_moneda_proyecto(base):
    """UC-01 paso 1 (enmienda de S1): la moneda elegida queda en `moneda_proyecto`, y la primera
    version no se valora con una lista de otra moneda (RF-65)."""
    ruta, _ = base
    assert proyectos.crear_proyecto_nuevo(ruta, "Obra en Bs", "Bs") == "Obra en Bs"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            proyecto = sesion.scalars(
                select(models.Proyecto).where(models.Proyecto.nombre == "Obra en Bs")
            ).one()
            filas = sesion.scalars(
                select(models.MonedaProyecto).where(
                    models.MonedaProyecto.proyecto_id == proyecto.id
                )
            ).all()
            assert [fila.moneda for fila in filas] == ["Bs"]
            with pytest.raises(hoja.HojaInvalida, match="Bs"):
                hoja.crear_primera_version(
                    sesion,
                    Catalogo(sesion),
                    "Obra en Bs",
                    hoja.Borrador(fecha=linea_base.FECHA_LINEA_BASE),
                    fuente="plano A-01",
                    responsable="Ing. Prueba",
                )
    finally:
        motor.dispose()


def test_sin_moneda_el_proyecto_no_declara_ninguna(base):
    ruta, _ = base
    proyectos.crear_proyecto_nuevo(ruta, "Obra sin moneda")
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            assert not sesion.scalars(select(models.MonedaProyecto)).all()
    finally:
        motor.dispose()
