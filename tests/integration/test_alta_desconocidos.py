"""UC-02, flujo 2a (INV-090, expediente C6.2): dar de alta los insumos desconocidos de la lista.

`docs/ERS.md` UC-02 2a: «el sistema los lista y ofrece darlos de alta o ignorarlos; los ignorados
no intervienen en el recalculo». La vista previa (`insumos_desconocidos`) no escribe; el alta solo
ocurre con la seleccion explicita de `dar_de_alta`, con codigo nuevo del tipo y precio solo en la
lista nueva. Oraculos: la linea base (`tests/fixtures/apu_linea_base.py`, trece materiales
distintos) y lo que la muestra de UC-02 cambia, calculado a mano
(`tests/fixtures/actualizacion_uc02.py`).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import actualizar_precios, plan_secuencial
from core.catalog import (
    Catalogo,
    crear_lista_desde_archivo,
    insumos_desconocidos,
    leer_lista_precios,
)
from core.contracts import ComposicionAPU, Dominio, LineaEquipo, LineaManoObra
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import CEMENTO, INCREMENTO_TOTAL, PRECIOS_NUEVOS
from tests.fixtures.base_con_pendiente import elaborar_en, guardar_en
from tests.fixtures.computo_auditado import items_auditados

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
FECHA_NUEVA = date(2026, 6, 1)
NUEVO = "Cemento blanco"
OTRO_NUEVO = "Impermeabilizante asfaltico"

#: La siembra numera los materiales MAT-001 ... MAT-NNN, uno por (descripcion, unidad) distinta de
#: la linea base (las variantes llevan sufijo): el primero dado de alta es el siguiente numero.
MATERIALES_SEMBRADOS = len(
    {(m.descripcion, m.unidad) for apu in linea_base.APUS_LINEA_BASE for m in apu.materiales}
)
CODIGO_ESPERADO = f"MAT-{MATERIALES_SEMBRADOS + 1:03d}"


def _archivo(tmp_path: Path, *filas_extra: str) -> Path:
    """La muestra de UC-02 mas las filas dadas: un CSV nuevo en `tmp_path`."""
    archivo = tmp_path / "lista_con_desconocidos.csv"
    texto = MUESTRA.read_text(encoding="utf-8").rstrip("\n")
    archivo.write_text("\n".join([texto, *filas_extra]) + "\n", encoding="utf-8")
    return archivo


def _crear(sesion, archivo: Path, dar_de_alta=()):
    return crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre="Lista 01/06/2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
        dar_de_alta=dar_de_alta,
    )


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def _precio(sesion, lista: models.ListaPrecios, insumo: models.Insumo):
    return sesion.scalar(
        select(models.PrecioInsumo.precio).where(
            models.PrecioInsumo.lista_id == lista.id,
            models.PrecioInsumo.insumo_id == insumo.id,
        )
    )


@pytest.fixture
def archivo(tmp_path):
    """La muestra con dos desconocidos del flujo 2a y un rechazado del 2b (cemento en m3)."""
    return _archivo(
        tmp_path,
        f"material,{NUEVO},saco,25",
        f"material,{OTRO_NUEVO},galon,40",
        f"material,{CEMENTO},m3,99",
    )


def test_la_vista_previa_lista_los_desconocidos_sin_crear_nada(sesion, archivo):
    insumos, listas = _contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios)

    vista = insumos_desconocidos(sesion, archivo)

    assert [(p.tipo, p.descripcion, p.unidad) for p in vista] == [
        (models.TipoInsumo.MATERIAL, NUEVO, "saco"),
        (models.TipoInsumo.MATERIAL, OTRO_NUEVO, "galon"),
    ]
    assert (_contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios)) == (
        insumos,
        listas,
    )


def test_el_elegido_se_da_de_alta_con_precio_solo_en_la_lista_nueva(sesion, archivo):
    anterior = Catalogo(sesion).lista_vigente(FECHA_NUEVA)
    elegido = next(p for p in insumos_desconocidos(sesion, archivo) if p.descripcion == NUEVO)

    resumen = _crear(sesion, archivo, dar_de_alta=[elegido])

    (alta,) = resumen.dados_de_alta
    assert (alta.codigo, alta.tipo, alta.descripcion, alta.unidad) == (
        CODIGO_ESPERADO,
        models.TipoInsumo.MATERIAL.value,
        NUEVO,
        "saco",
    )
    assert _precio(sesion, resumen.lista, alta) == elegido.precio
    assert _precio(sesion, anterior, alta) is None
    # Los ignorados (2a) y el rechazado (2b) siguen en `desconocidos`; el dado de alta no.
    assert [(p.descripcion, p.unidad) for p in resumen.desconocidos] == [
        (OTRO_NUEVO, "galon"),
        (CEMENTO, "m3"),
    ]
    catalogo = {insumo.descripcion for insumo in Catalogo(sesion).insumos()}
    assert NUEVO in catalogo
    assert OTRO_NUEVO not in catalogo


def test_sin_eleccion_nada_se_da_de_alta(sesion, archivo):
    insumos = _contar(sesion, models.Insumo)

    resumen = _crear(sesion, archivo)

    assert resumen.dados_de_alta == ()
    assert [p.descripcion for p in resumen.desconocidos] == [NUEVO, OTRO_NUEVO, CEMENTO]
    assert _contar(sesion, models.Insumo) == insumos


def test_revalorar_con_alta_da_el_incremento_calculado_sin_ella(sesion, archivo):
    """El dado de alta no esta en ningun APU ni en la lista anterior: no es un cambio de precio.

    Una sola corrida, con alta; el oraculo es el incremento del caso sin alta, calculado a mano en
    `tests/fixtures/actualizacion_uc02.py` (el comparativo sin alta lo fija
    `test_actualizacion_precios.py`)."""
    proyecto = sembrar(sesion)
    guardar_en(sesion, proyecto, elaborar_en(sesion, items_auditados()))
    resumen = _crear(sesion, archivo, dar_de_alta=insumos_desconocidos(sesion, archivo))
    assert len(resumen.dados_de_alta) == 2

    nuevo, comparativo = actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        resumen.lista,
        "002",
        plan=plan_secuencial,
    )

    assert comparativo.insumos_afectados == len(PRECIOS_NUEVOS)
    assert comparativo.variacion == INCREMENTO_TOTAL
    assert nuevo.presupuesto.total == comparativo.total_nuevo


@pytest.mark.parametrize("descripcion, unidad", [(CEMENTO, "saco"), (CEMENTO, "m3")])
def test_elegir_un_casado_o_un_rechazado_se_rechaza_sin_escribir(
    sesion, archivo, descripcion, unidad
):
    """Un casado ya existe; un rechazado del flujo 2b tiene otra unidad que el catalogo: ninguno
    se da de alta, y la validacion ocurre antes de crear la lista."""
    elegido = next(
        p for p in leer_lista_precios(archivo) if (p.descripcion, p.unidad) == (descripcion, unidad)
    )
    insumos, listas = _contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios)

    with pytest.raises(ValueError, match="no es un insumo desconocido"):
        _crear(sesion, archivo, dar_de_alta=[elegido])

    assert (_contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios)) == (
        insumos,
        listas,
    )


def test_equipo_y_mano_de_obra_se_dan_de_alta_sin_unidad_y_un_apu_los_reutiliza(sesion, tmp_path):
    """Arq N-1: una lista escribe equipos y mano de obra con unidad («dia»); el catalogo los lleva
    sin ella (`lineas_de`). El alta los guarda sin unidad, con codigo EQU-/MO- nuevo, y el APU que
    se compone despues con esos insumos y esos precios los reutiliza: ningun homonimo nuevo."""
    archivo = _archivo(
        tmp_path,
        "equipo,Carretilla para construccion,dia,12",
        "mano_obra,Plomero de primera,dia,30",
    )
    equipos = len(Catalogo(sesion).insumos(models.TipoInsumo.EQUIPO))
    obreros = len(Catalogo(sesion).insumos(models.TipoInsumo.MANO_OBRA))
    # El siguiente numero de cada tipo: las variantes («-B») no cuentan como numero propio.
    base_equipos = len({i.codigo[:7] for i in Catalogo(sesion).insumos(models.TipoInsumo.EQUIPO)})

    resumen = _crear(sesion, archivo, dar_de_alta=insumos_desconocidos(sesion, archivo))

    equipo, obrero = resumen.dados_de_alta
    assert (equipo.codigo, equipo.unidad) == (f"EQU-{base_equipos + 1:03d}", None)
    assert (obrero.codigo, obrero.unidad) == (f"MO-{obreros + 1:03d}", None)
    assert resumen.desconocidos == ()
    assert _precio(sesion, resumen.lista, equipo) == Decimal(12)

    apu = ComposicionAPU(
        codigo_partida="C6-99-APU",
        descripcion="Partida que usa lo dado de alta",
        unidad="m3",
        rendimiento=Decimal(10),
        equipos=(
            LineaEquipo(
                descripcion="Carretilla para construccion",
                cantidad=Decimal(1),
                precio=Decimal(12),
                depreciacion=Decimal(1),
            ),
        ),
        mano_obra=(
            LineaManoObra(
                descripcion="Plomero de primera", cantidad=Decimal(1), sueldo=Decimal(30)
            ),
        ),
    )
    carga = Catalogo(sesion).cargar_composicion(
        apu, resumen.lista, Dominio.CIVIL, FECHA_NUEVA, "prueba de reutilizacion"
    )

    assert carga.insumos_nuevos == [] and carga.variantes == []
    assert len(Catalogo(sesion).insumos(models.TipoInsumo.EQUIPO)) == equipos + 1
    assert len(Catalogo(sesion).insumos(models.TipoInsumo.MANO_OBRA)) == obreros + 1


def test_un_desconocido_repetido_se_da_de_alta_una_sola_vez(sesion, tmp_path):
    """QA N-QA-5 (M3): dos filas con la misma identidad de catalogo (la segunda con otra grafia),
    las dos elegidas, dan una sola alta, y el precio llega a la lista nueva."""
    archivo = _archivo(tmp_path, f"material,{NUEVO},saco,25", f"material,{NUEVO.upper()},Saco,25")
    insumos = _contar(sesion, models.Insumo)
    vista = insumos_desconocidos(sesion, archivo)
    assert len(vista) == 2

    resumen = _crear(sesion, archivo, dar_de_alta=vista)

    (alta,) = resumen.dados_de_alta
    assert _contar(sesion, models.Insumo) == insumos + 1
    assert _precio(sesion, resumen.lista, alta) == Decimal(25)
    assert resumen.desconocidos == ()


def test_un_desconocido_repetido_con_precios_distintos_se_rechaza(sesion, tmp_path):
    archivo = _archivo(tmp_path, f"material,{NUEVO},saco,25", f"material,{NUEVO},saco,26")
    insumos, listas = _contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios)
    lineas_muestra = len(leer_lista_precios(MUESTRA))

    with pytest.raises(ValueError, match=rf"filas {lineas_muestra + 2}, {lineas_muestra + 3}:"):
        _crear(sesion, archivo, dar_de_alta=insumos_desconocidos(sesion, archivo))

    assert (_contar(sesion, models.Insumo), _contar(sesion, models.ListaPrecios)) == (
        insumos,
        listas,
    )


@pytest.mark.parametrize(
    ("tipo", "descripcion", "unidad", "patron"),
    [
        (models.TipoInsumo.MATERIAL, "   ", "saco", "vacia"),
        (models.TipoInsumo.MATERIAL, CEMENTO, "saco", "ya esta en el catalogo"),
        (models.TipoInsumo.MATERIAL, "  CEMENTO portland ", "Saco", "ya esta en el catalogo"),
        (models.TipoInsumo.EQUIPO, "retroexcavadora", "dia", "ya esta en el catalogo"),
        (models.TipoInsumo.MANO_OBRA, "AYUDANTE", None, "ya esta en el catalogo"),
    ],
    ids=["vacia", "existente", "otra-grafia", "equipo-con-unidad", "mano-de-obra"],
)
def test_la_guardia_del_alta_usa_la_identidad_del_catalogo(
    sesion, tipo, descripcion, unidad, patron
):
    """QA N-QA-5 (M16): el alta directa rechaza la descripcion vacia y todo insumo que el catalogo
    ya tiene con la misma identidad normalizada, aunque se escriba con otra grafia."""
    insumos = _contar(sesion, models.Insumo)

    with pytest.raises(ValueError, match=patron):
        Catalogo(sesion).dar_de_alta_insumo(tipo, descripcion, unidad)

    assert _contar(sesion, models.Insumo) == insumos


def test_un_equipo_con_dos_unidades_es_una_sola_alta(sesion, tmp_path):
    """QA M11: la identidad del alta de equipos y mano de obra no usa la unidad (el catalogo los
    lleva sin ella): dos filas del mismo equipo, «dia» y «hr», dan una alta, no dos."""
    archivo = _archivo(
        tmp_path, "equipo,Compactador de placa,dia,40", "equipo,Compactador de placa,hr,40"
    )
    vista = insumos_desconocidos(sesion, archivo)
    assert len(vista) == 2
    equipos = len(Catalogo(sesion).insumos(models.TipoInsumo.EQUIPO))

    resumen = _crear(sesion, archivo, dar_de_alta=vista)

    (alta,) = resumen.dados_de_alta
    assert alta.unidad is None
    assert len(Catalogo(sesion).insumos(models.TipoInsumo.EQUIPO)) == equipos + 1
    assert _precio(sesion, resumen.lista, alta) == Decimal(40)
    assert resumen.desconocidos == ()


def test_un_equipo_con_dos_unidades_y_precios_distintos_se_rechaza(sesion, tmp_path):
    """QA M11: las mismas dos filas con precios distintos son una sola alta con dos precios."""
    archivo = _archivo(
        tmp_path, "equipo,Compactador de placa,dia,40", "equipo,Compactador de placa,hr,45"
    )
    insumos = _contar(sesion, models.Insumo)

    with pytest.raises(ValueError, match="una sola vez"):
        _crear(sesion, archivo, dar_de_alta=insumos_desconocidos(sesion, archivo))

    assert _contar(sesion, models.Insumo) == insumos
