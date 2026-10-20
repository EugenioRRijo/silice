"""La base de las vistas de la hoja (T10, 3b-1): montos, version por omision, resumen y R17.

Oraculos a mano: la regla de la version por omision es la de la pagina clasica (P:417-421: las no
descartadas, o todas si todas lo estan; la vigente, o la ultima); los montos, `formatear_decimal`
a dos decimales (NORMAS.md §2) y el exacto con `format(x, "f")`; el resumen de OF-001 usa los
literales de la memoria (total 2 703,86 USD).
"""

from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio.modelo import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Punto,
    SuperficiePunto,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from aplicacion import hoja, hoja_vista
from aplicacion.hoja_borradores import Registro
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import Severidad
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

D = Decimal
HOY = date(2026, 10, 19)


def _fila(codigo: str, *, vigente=False, descartada=False) -> hoja.FilaVersion:
    return hoja.FilaVersion(codigo, HOY, "", "", vigente, descartada, 0)


@pytest.mark.parametrize(
    ("valor", "texto", "exacto"),
    [
        (D("2703.856"), "2703.86", "2703.856"),
        (D("0.005"), "0.01", "0.005"),
        (D("3"), "3.00", "3"),
        (D("1E+1"), "10.00", "10"),
        (
            D("123456789012345678901234567890.1234"),
            "123456789012345678901234567890.12",
            "123456789012345678901234567890.1234",
        ),
    ],
)
def test_un_monto_es_texto_a_dos_decimales_y_exacto_sin_notacion_cientifica(valor, texto, exacto):
    m = hoja_vista.monto(valor)
    assert (m.texto, m.exacto) == (texto, exacto)


def test_version_por_omision_es_la_vigente_entre_las_no_descartadas():
    filas = [_fila("001"), _fila("002"), _fila("003", vigente=True)]
    assert hoja_vista.version_por_omision(filas) == "003"


def test_con_la_ultima_descartada_la_vigente_pasa_a_ser_otra():
    filas = [_fila("001"), _fila("002", vigente=True), _fila("003", descartada=True)]
    assert hoja_vista.version_por_omision(filas) == "002"


def test_con_todas_descartadas_se_ofrece_la_ultima():
    filas = [_fila("001", descartada=True), _fila("002", descartada=True)]
    assert hoja_vista.version_por_omision(filas) == "002"


def test_sin_versiones_no_hay_version_por_omision():
    assert hoja_vista.version_por_omision([]) is None


def test_sin_vigente_entre_las_no_descartadas_se_toma_la_ultima_no_descartada():
    filas = [_fila("001"), _fila("002")]
    assert hoja_vista.version_por_omision(filas) == "002"


def test_mensaje_de_la_instantanea_solo_si_se_creo_alguna():
    assert hoja_vista.mensaje_instantanea(0) is None
    assert hoja_vista.mensaje_instantanea(3) == (
        "Se creó y registró la instantánea de las composiciones de esta versión (3 partidas): "
        "sus APU ya no cambian si cambia el catálogo."
    )


@pytest.fixture(scope="module")
def _of001(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("vista_hoja")
    plantilla = plantilla_of001(carpeta / "of001.db")
    copia = carpeta / "copia.db"
    shutil.copyfile(plantilla, copia)
    motor = crear_motor(f"sqlite:///{Path(copia).as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            abierta = hoja.abrir_version(
                sesion, Catalogo(sesion), NOMBRE_OF001, "001", fecha_evaluacion=HOY
            )
    finally:
        motor.dispose()
    return abierta


def test_el_resumen_de_of001_da_el_total_de_la_memoria_sin_cambios(_of001):
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", _of001.borrador, _of001)
    r = hoja_vista.resumen(vivo)
    assert abs(Decimal(r.total.exacto) - D("2703.86")) <= D("0.01")
    assert (r.rev, r.moneda, r.cambios, r.pendientes_catalogo, r.hay_plan) == (
        0,
        "USD",
        0,
        0,
        True,
    )
    assert r.guardado_como is None and r.version_mas_nueva is None
    assert all(isinstance(h.total, int) for h in r.hallazgos)


def test_el_resumen_cuenta_los_cambios_contra_la_version_abierta(_of001):
    from dataclasses import replace

    editado = replace(
        _of001.borrador, parametros=replace(_of001.borrador.parametros, administracion=D("0.20"))
    )
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", editado, _of001)
    r = hoja_vista.resumen(vivo)
    assert r.cambios == 1
    assert abs(Decimal(r.total.exacto) - D("2821.42")) <= D("0.01")


def _espacio_con_un_punto_sin_fuente() -> Espacio:
    lev = OrigenMedida(
        id="LEV",
        tipo=TipoOrigen.LEVANTAMIENTO,
        referencia={"fecha": "2026-10-01", "responsable": "EP"},
    )
    ambiente = Ambiente("A", "Bano", D("0"), D("0"), D("3"), D("2"), D("2.5"), "LEV")
    punto = Punto(
        id="P2",
        nombre="lavamanos",
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id="A",
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("2"), D("0"), D("0.6")),
        origen_id="LEV",
        fuente_id=None,
        especificaciones={"diametro": '1/2"', "llave_de_paso": "si"},
    )
    return Espacio(origenes=(lev,), ambientes=(ambiente,), puntos=(punto,))


def test_elaborar_agrega_r17_y_no_la_deja_en_el_borrador():
    """R17 se calcula en cada elaboracion y no se guarda en el borrador (P:286-296)."""
    borrador = hoja.Borrador(fecha=HOY, espacio=_espacio_con_un_punto_sin_fuente())
    resultado = hoja_vista.elaborar(borrador)
    r17 = [h for h in resultado.elaboracion.informe.hallazgos if h.regla == "R17"]
    assert [(h.severidad, h.origen_ids) for h in r17] == [
        (Severidad.ADVERTENCIA, ("esp_puntos:P2",))
    ]
    assert "El punto P2 (lavamanos) no tiene fuente" in r17[0].descripcion
    assert borrador.reglas_extra == ()


def test_la_cache_del_calculo_se_reutiliza_por_rev(_of001):
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", _of001.borrador, _of001)
    primero = hoja_vista.calculo(vivo)
    segundo = hoja_vista.calculo(vivo)
    assert segundo[0] is primero[0] and segundo[1] is primero[1]
    assert vivo.calculo is not None and vivo.calculo[0] == 0


def test_la_base_abierta_describe_la_version(_of001):
    vivo = Registro().crear("f", "caso", NOMBRE_OF001, "001", _of001.borrador, _of001)
    b = hoja_vista.base(vivo, vigente="001")
    assert (b.proyecto, b.version, b.vigente, b.espacio_de, b.solo_lectura, b.moneda) == (
        NOMBRE_OF001,
        "001",
        "001",
        "001",
        False,
        "USD",
    )
    assert b.lista == _of001.lista


def test_la_base_de_un_proyecto_sin_versiones_es_en_blanco():
    vivo = Registro().crear("f", "caso", "Nuevo", None, hoja.Borrador(fecha=HOY), None)
    b = hoja_vista.base(vivo, vigente=None)
    assert (b.proyecto, b.version, b.lista, b.espacio_de, b.solo_lectura) == (
        "Nuevo",
        None,
        None,
        None,
        False,
    )
