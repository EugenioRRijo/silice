"""La primera version de un proyecto nuevo (RI-7 de la integracion final), contra una base real.

`ui.hoja.crear_primera_version` guarda el borrador de un proyecto que todavia no tiene ninguna
version: el camino «crear un presupuesto nuevo a partir del espacio». Oraculos independientes: el
literal 2 703,86 USD de la memoria de OF-001, el total de la hoja manual (version `001` del proyecto
sembrado con el mismo espacio y los mismos parametros), consultas propias a `models.*` y a las
tablas `esp_*`. Cada prueba trabaja sobre una copia de un archivo temporal sembrado una sola vez.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import load_workbook
from sqlalchemy import func, select, text

from adapters.espacio import cargar_espacio
from aplicacion import hoja
from core import models
from core.budget import crear_proyecto
from core.budget.instantanea import composiciones_de_version
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import ParametrosCosto
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

D = Decimal
NUEVO = "Proyecto nuevo: bano de la oficina"
FUENTE = "medidas tomadas en sitio, acta 3"
RESPONSABLE = "Ing. Prueba"
AHORA = datetime(2026, 10, 5, 18, 0, 0)
TOTAL_MEMORIA = D("2703.86")


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("primera") / "of001.db")


@pytest.fixture
def base(_plantilla, tmp_path):
    """Sesion sobre una copia con un proyecto NUEVO (sin versiones) ademas del sembrado."""
    copia = tmp_path / "copia.db"
    shutil.copy(_plantilla, copia)
    motor = crear_motor(f"sqlite:///{copia.as_posix()}")
    with abrir_sesion(motor) as sesion:
        crear_proyecto(sesion, NUEVO)
        sesion.commit()
        yield sesion, Catalogo(sesion)
    motor.dispose()


def _borrador(**cambios) -> hoja.Borrador:
    return replace(
        hoja.Borrador(
            fecha=caso_of001.FECHA,
            moneda=caso_of001.MONEDA,
            espacio=espacio_of001(),
            parametros=caso_ti001.PARAMETROS,
        ),
        **cambios,
    )


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def _filas_esp(sesion) -> int:
    return sesion.execute(text("SELECT count(*) FROM esp_ambientes")).scalar_one()


def _crear(base, borrador=None, **opciones):
    sesion, catalogo = base
    opciones.setdefault("fuente", FUENTE)
    opciones.setdefault("responsable", RESPONSABLE)
    opciones.setdefault("ahora", AHORA)
    return hoja.crear_primera_version(
        sesion, catalogo, NUEVO, borrador if borrador is not None else _borrador(), **opciones
    )


def _modelo(sesion, codigo: str, proyecto: str = NUEVO) -> models.Presupuesto:
    return sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one()


# --- el camino feliz -----------------------------------------------------------------------------


def test_la_primera_version_se_guarda_con_el_total_de_la_memoria(base):
    sesion, _ = base
    guardada = _crear(base)

    assert guardada.codigo == "001"
    assert abs(guardada.total - TOTAL_MEMORIA) <= D("0.01")
    assert hoja.codigo_vigente(sesion, NUEVO) == "001"


def test_el_total_es_el_de_la_hoja_manual_con_los_mismos_parametros(base):
    sesion, catalogo = base
    manual = hoja.abrir_version(sesion, catalogo, NOMBRE_OF001, "001").guardada.presupuesto.total
    guardada = _crear(base)

    assert guardada.total == manual
    reabierta = hoja.abrir_version(sesion, catalogo, NUEVO, "001")
    assert reabierta.guardada.presupuesto.total == manual


def test_se_reabre_igual_con_su_espacio_copiado_con_la_clave_de_la_version(base):
    sesion, catalogo = base
    _crear(base)

    reabierta = hoja.abrir_version(sesion, catalogo, NUEVO, "001")
    assert reabierta.borrador.espacio == espacio_of001()
    assert reabierta.espacio_de == "001"
    nueva = _modelo(sesion, "001")
    assert len(cargar_espacio(sesion, nueva.id).ambientes) == 6
    # el espacio de la hoja manual sigue intacto: 6 ambientes de cada version
    assert _filas_esp(sesion) == 12


def test_guarda_los_parametros_del_borrador_y_la_lista_vigente_a_la_fecha(base):
    sesion, _ = base
    parametros = ParametrosCosto(
        fcas=D("7"), bono_alimentacion=D("2"), administracion=D("0.2"), utilidad=D("0.05")
    )
    _crear(base, _borrador(parametros=parametros))

    modelo = _modelo(sesion, "001")
    assert (
        modelo.fcas,
        modelo.bono_alimentacion,
        modelo.administracion,
        modelo.utilidad,
    ) == (D("7"), D("2"), D("0.2"), D("0.05"))
    assert modelo.lista_precios.nombre == "Lista MaPreX jul-2026 (OF-001)"
    assert modelo.fecha == caso_of001.FECHA


def test_la_instantanea_congela_las_composiciones_de_cada_partida_derivada(base):
    sesion, _ = base
    _crear(base)

    modelo = _modelo(sesion, "001")
    partidas = {r.partida.codigo for r in modelo.partidas}
    assert partidas
    assert set(composiciones_de_version(sesion, modelo)) == partidas


def test_el_registro_de_creacion_es_exactamente_uno_con_fuente_y_responsable(base):
    sesion, _ = base
    _crear(base)

    registros = hoja.registros_de_version(sesion, NUEVO, "001")
    assert [
        (r.objeto, r.clave, r.campo, r.valor_anterior, r.valor_nuevo, r.fuente, r.responsable)
        for r in registros
    ] == [("version", "001", "creacion", "", "001", FUENTE, RESPONSABLE)]
    assert registros[0].fecha_hora == AHORA
    nacida = _modelo(sesion, "001")
    fila = sesion.scalars(select(models.RegistroCambio)).one()
    assert (fila.version_origen_id, fila.version_resultante_id) == (None, nacida.id)
    assert (
        sesion.get(models.VersionOrigen, nacida.id) is None
    )  # nace de cero: sin version de origen


def test_el_historial_dice_que_la_001_nacio_de_cero_con_un_registro(base):
    sesion, _ = base
    _crear(base)

    filas = hoja.historial_de_versiones(sesion, NUEVO)
    assert [(f.codigo, f.motivo, f.origen, f.vigente, f.cambios) for f in filas] == [
        ("001", "", "", True, 1)
    ]


def test_sin_plan_en_el_borrador_la_primera_version_lleva_el_plan_secuencial(base):
    sesion, catalogo = base
    _crear(base)

    abierta = hoja.abrir_version(sesion, catalogo, NUEVO, "001")
    assert abierta.borrador.plan
    assert abierta.guardada.presupuesto.curva
    assert abierta.guardada.presupuesto.curva[-1].acumulado == abierta.guardada.presupuesto.total


def test_el_codigo_pedido_se_respeta_y_el_siguiente_es_el_que_sigue(base):
    sesion, catalogo = base
    guardada = _crear(base, codigo="OF-001")
    assert guardada.codigo == "OF-001"
    abierta = hoja.abrir_version(sesion, catalogo, NUEVO, "OF-001")
    editado = replace(
        abierta.borrador, parametros=replace(abierta.borrador.parametros, fcas=D("7"))
    )
    segunda = hoja.guardar_version(
        sesion, catalogo, abierta, editado, fuente=FUENTE, responsable=RESPONSABLE
    )
    assert segunda.codigo == "OF-002"


def test_el_excel_de_la_primera_version_incluye_su_trazabilidad(base, tmp_path):
    sesion, catalogo = base
    _crear(base)
    abierta = hoja.abrir_version(sesion, catalogo, NUEVO, "001")
    resultado = hoja.elaborar_borrador(abierta.borrador, codigo="001")

    ruta = hoja.exportar_excel(
        tmp_path / "primera.xlsx",
        resultado,
        abierta.borrador,
        trazabilidad=hoja.tabla_de_trazabilidad(sesion, NUEVO, "001"),
        precios=hoja.precios_de_version(sesion, NUEVO, "001"),
    )
    libro = load_workbook(ruta)
    assert libro["Trazabilidad"].max_row == 2  # encabezado + el registro de creacion


# --- despues de la primera, el flujo normal -------------------------------------------------------


def test_editar_y_guardar_despues_de_la_primera_produce_la_002(base):
    sesion, catalogo = base
    _crear(base)
    abierta = hoja.abrir_version(sesion, catalogo, NUEVO, "001")
    editado = replace(
        abierta.borrador, parametros=replace(abierta.borrador.parametros, fcas=D("7"))
    )

    segunda = hoja.guardar_version(
        sesion,
        catalogo,
        abierta,
        editado,
        fuente="el FCAS lo fija la convencion",
        responsable=RESPONSABLE,
        ahora=AHORA,
    )

    assert segunda.codigo == "002" and segunda.cambios == 1
    filas = hoja.historial_de_versiones(sesion, NUEVO)
    assert [(f.codigo, f.motivo, f.origen, f.vigente) for f in filas] == [
        ("001", "", "", False),
        ("002", "edicion", "001", True),
    ]


# --- rechazos: no dejan filas ---------------------------------------------------------------------


def _cuenta(sesion) -> tuple[int, int, int, int]:
    return (
        _contar(sesion, models.Presupuesto),
        _contar(sesion, models.RegistroCambio),
        _contar(sesion, models.ComposicionVersion),
        _filas_esp(sesion),
    )


@pytest.mark.parametrize(
    ("fuente", "responsable", "palabra"),
    [("", RESPONSABLE, "fuente"), ("   ", RESPONSABLE, "fuente"), (FUENTE, "", "responsable")],
)
def test_sin_fuente_o_sin_responsable_se_rechaza_y_no_deja_filas(
    base, fuente, responsable, palabra
):
    sesion, _ = base
    antes = _cuenta(sesion)

    with pytest.raises(hoja.HojaInvalida, match=palabra):
        _crear(base, fuente=fuente, responsable=responsable)

    assert _cuenta(sesion) == antes


def test_guardar_dos_veces_seguidas_la_primera_no_duplica(base):
    sesion, _ = base
    _crear(base)
    despues_de_la_primera = _cuenta(sesion)

    with pytest.raises(hoja.HojaInvalida, match="ya tiene versiones"):
        _crear(base)

    assert _cuenta(sesion) == despues_de_la_primera
    assert [f.codigo for f in hoja.historial_de_versiones(sesion, NUEVO)] == ["001"]


def test_un_proyecto_con_versiones_no_admite_primera_version(base):
    sesion, catalogo = base
    antes = _cuenta(sesion)

    with pytest.raises(hoja.HojaInvalida, match="ya tiene versiones"):
        hoja.crear_primera_version(
            sesion, catalogo, NOMBRE_OF001, _borrador(), fuente=FUENTE, responsable=RESPONSABLE
        )

    assert _cuenta(sesion) == antes


def test_un_proyecto_que_no_existe_se_rechaza_diciendo_como_crearlo(base):
    sesion, catalogo = base
    with pytest.raises(hoja.HojaInvalida, match="no existe"):
        hoja.crear_primera_version(
            sesion, catalogo, "Otro", _borrador(), fuente=FUENTE, responsable=RESPONSABLE
        )


def test_una_hoja_vacia_no_se_guarda(base):
    sesion, _ = base
    antes = _cuenta(sesion)

    with pytest.raises(hoja.HojaInvalida, match="vacia"):
        _crear(base, hoja.Borrador(fecha=caso_of001.FECHA, moneda=caso_of001.MONEDA))

    assert _cuenta(sesion) == antes


def test_si_el_gancho_del_espacio_falla_no_queda_nada(base, monkeypatch):
    """Una sola Session: si no se puede copiar el espacio, tampoco existe la version."""
    sesion, _ = base
    antes = _cuenta(sesion)

    def roto(*_):
        raise RuntimeError("disco lleno")

    monkeypatch.setattr(hoja, "guardar_espacio", roto)
    with pytest.raises(RuntimeError, match="disco lleno"):
        _crear(base)

    assert _cuenta(sesion) == antes
    assert hoja.historial_de_versiones(sesion, NUEVO) == []
    # y el proyecto sigue sin versiones: se puede volver a intentar
    monkeypatch.undo()
    assert _crear(base).codigo == "001"


def test_sin_lista_de_precios_vigente_el_error_lo_dice_y_no_inventa_precios(base):
    sesion, _ = base
    antes = _cuenta(sesion)

    with pytest.raises(hoja.HojaInvalida, match="lista de precios"):
        _crear(base, _borrador(fecha=date(2000, 1, 1)))

    assert _cuenta(sesion) == antes


# --- el motivo que la pantalla muestra en el boton --------------------------------------------


def test_el_motivo_para_no_crear_la_primera_dice_que_falta_en_orden():
    vacio = hoja.Borrador(fecha=caso_of001.FECHA)
    assert "vacia" in hoja.motivo_para_no_crear_primera(vacio, FUENTE, RESPONSABLE)
    assert "fuente" in hoja.motivo_para_no_crear_primera(_borrador(), " ", RESPONSABLE)
    assert "responsable" in hoja.motivo_para_no_crear_primera(_borrador(), FUENTE, "")
    assert hoja.motivo_para_no_crear_primera(_borrador(), FUENTE, RESPONSABLE) is None
