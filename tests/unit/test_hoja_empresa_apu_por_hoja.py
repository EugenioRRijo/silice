"""F5 vial, tarea 4: el perfil hermano `apu_por_hoja` (un APU por hoja, solo valores) y su mapeo.

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §7 (punto 4, opción B):
un tipo de perfil hermano en `adapters/hoja_empresa/` con su lector, que produce el mismo
`LibroLeido` / `ApuLeido` y usa la misma guardia; `fusion/mapeo.py` arma la composición del núcleo
con el desperdicio dentro de la cantidad (punto 1, opción B) y devuelve la traza aparte.

El libro es el FICTICIO de `tests/fixtures/libro_apu_por_hoja.py`; los oráculos son los de su
memoria de cálculo, escritos a mano.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.lector_apu_por_hoja import leer_libro_apu_por_hoja
from adapters.hoja_empresa.modelo import Celda, LibroNoInterpretable, Rotulo, TipoInsumo
from adapters.hoja_empresa.perfil import PerfilInvalido
from adapters.hoja_empresa.perfil_apu_por_hoja import cargar_perfil_apu_por_hoja
from core.contracts.apu import ParametrosCosto
from core.costing.motor import calcular_apu
from fusion.mapeo import composicion_de_apu_por_hoja
from tests.fixtures.libro_apu_por_hoja import APUS, ApuFicticio, Material, libro_apu

D = Decimal


@pytest.fixture(scope="module")
def libro():
    return leer_libro_apu_por_hoja(libro_apu(), "frente_ficticio.xlsx")


def test_el_perfil_del_paquete_carga_y_se_valida():
    perfil = cargar_perfil_apu_por_hoja("apu_por_hoja")
    assert perfil.nombre == "apu_por_hoja"
    assert perfil.prefijo_hoja == "APU"
    assert set(perfil.bloques) == {"materiales", "equipos", "mano_obra"}


def test_un_perfil_incompleto_se_rechaza_al_cargar(tmp_path: Path):
    crudo = json.loads(
        (
            Path(__file__).resolve().parents[2] / "adapters/hoja_empresa/perfiles/apu_por_hoja.json"
        ).read_text(encoding="utf-8")
    )
    del crudo["bloques"]["equipos"]
    (tmp_path / "otro.json").write_text(json.dumps({**crudo, "nombre": "otro"}), encoding="utf-8")
    with pytest.raises(PerfilInvalido, match="bloques: faltan"):
        cargar_perfil_apu_por_hoja("otro", carpetas=(tmp_path,))


def test_lee_una_hoja_por_partida_con_su_cabecera(libro):
    assert libro.perfil == "apu_por_hoja"
    assert [a.hoja for a in libro.apus] == ["APU 1", "APU 2", "APU 3", "APU 4", "APU 5"]
    apu = libro.apu("APU 1")
    assert (apu.numero, apu.codigo_partida, apu.titulo, apu.unidad) == (
        1,
        "VF-001",
        "Riego de adherencia ficticio",
        "m2",
    )
    assert (apu.cantidad, apu.rendimiento) == (D("1000"), D("2000"))
    assert (apu.prestaciones, apu.administracion, apu.utilidad) == (D("2.5"), D("0.15"), D("0.1"))
    assert (apu.financiamiento, apu.impuesto) == (D("0"), D("0"))
    assert apu.guardados[Rotulo.PU] == D("2.08")
    assert apu.rotulos[Rotulo.PU] == Celda("APU 1", "G33")


def test_lee_todos_los_renglones_con_o_sin_numero(libro):
    apu = libro.apu("APU 1")
    assert [(x.tipo, x.codigo, x.descripcion, x.cantidad) for x in apu.lineas] == [
        (TipoInsumo.MATERIAL, "1", "Emulsión asfáltica ficticia", D("0.5")),
        (TipoInsumo.MATERIAL, "", "Arena de secado ficticia", D("0.002")),
        (TipoInsumo.EQUIPO, "1", "Camión irrigador ficticio", D("1")),
        (TipoInsumo.EQUIPO, "2", "Barredora ficticia", D("1")),
        (TipoInsumo.MANO_OBRA, "1", "Operador ficticio", D("2")),
        (TipoInsumo.MANO_OBRA, "", "Ayudante ficticio", D("3")),
    ]
    emulsion, arena, _, barredora, *_ = apu.lineas
    assert (emulsion.unidad, emulsion.desperdicio, emulsion.precio) == ("lt", D("4"), D("2"))
    assert emulsion.celda_cantidad == Celda("APU 1", "D9")
    assert arena.desperdicio == D("0")
    assert barredora.depreciacion == D("0.5")
    assert len(libro.apu("APU 3").lineas) == 6 + 1 + 1


def test_bono_financiamiento_e_impuesto(libro):
    assert libro.apu("APU 4").financiamiento == D("0.02")
    cinco = libro.apu("APU 5")
    assert [x.bono for x in cinco.lineas] == [D("5")]
    assert cinco.impuesto == D("0.16")


def test_una_hoja_sin_precio_unitario_no_se_interpreta():
    rota = ApuFicticio(
        9,
        "VF-009",
        "Sin pie ficticio",
        "m2",
        "1",
        "1",
        materiales=(Material(1, "Cosa ficticia", "kg", "1", "0", "1"),),
    )
    datos = libro_apu((rota,))
    import io

    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(datos))
    hoja = wb["APU 9"]
    for fila in hoja.iter_rows():
        for celda in fila:
            if celda.value == "PRECIO UNITARIO":
                celda.value = "Otra cosa"
    salida = io.BytesIO()
    wb.save(salida)
    with pytest.raises(LibroNoInterpretable, match="APU 9.*PRECIO UNITARIO"):
        leer_libro_apu_por_hoja(salida.getvalue(), "roto.xlsx")


def test_un_libro_sin_hojas_de_apu_se_rechaza():
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    wb.active.title = "Hoja1"
    salida = io.BytesIO()
    wb.save(salida)
    with pytest.raises(ArchivoRechazado, match="ninguna hoja de APU"):
        leer_libro_apu_por_hoja(salida.getvalue(), "vacio.xlsx")


def test_la_misma_guardia_de_siempre():
    with pytest.raises(ArchivoRechazado):
        leer_libro_apu_por_hoja(b"esto no es un xlsx", "malo.xlsx")


# --- mapeo al núcleo --------------------------------------------------------------------------


def test_el_mapeo_pone_el_desperdicio_dentro_de_la_cantidad_y_da_la_traza(libro):
    composicion, parametros, trazas = composicion_de_apu_por_hoja(libro.apu("APU 1"))
    assert [(m.descripcion, m.cantidad) for m in composicion.materiales] == [
        ("Emulsión asfáltica ficticia", D("0.52")),
        ("Arena de secado ficticia", D("0.002")),
    ]
    assert [(t.descripcion, t.cantidad_neta, t.desperdicio_pct, t.cantidad) for t in trazas] == [
        ("Emulsión asfáltica ficticia", D("0.5"), D("4"), D("0.52"))
    ]
    assert parametros == ParametrosCosto(
        fcas=D("2.5"), bono_alimentacion=D("0"), administracion=D("0.15"), utilidad=D("0.1")
    )
    # memoria: 1,6425 × 1,15 × 1,10
    assert calcular_apu(composicion, parametros).precio_unitario == D("2.0777625")


def test_el_mapeo_de_la_demarcacion_da_el_precio_exacto(libro):
    composicion, parametros, _ = composicion_de_apu_por_hoja(libro.apu("APU 3"))
    assert calcular_apu(composicion, parametros).precio_unitario == D("0.81213")


def test_el_fixture_es_el_de_la_memoria():
    assert [a.numero for a in APUS] == [1, 2, 3, 4, 5]
