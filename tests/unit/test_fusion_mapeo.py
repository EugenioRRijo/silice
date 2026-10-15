"""Del libro de la empresa a los contratos del núcleo sin tocar el núcleo (Silice 1.5, RF-103;
spec F-D1, F-D7 y ruling RL-8).

Oráculo: la memoria de cálculo a mano del fixture (`MEMORIA`) y, para cada variante (destajo,
factor escrito en la fórmula, divisor literal de equipos), la cuenta de la plantilla hecha a mano
en el docstring de la prueba. El motor del núcleo debe dar el P.U. de la empresa EXACTO (Decimal,
sin redondeo): la plantilla y el núcleo hacen la misma aritmética.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import LibroNoInterpretable, Portada
from core.contracts.apu import ModalidadManoObra
from core.contracts.item_computo import OrigenTipo
from core.contracts.unidades import normalizar_unidad
from fusion.mapeo import (
    DESCRIPCION_HERRAMIENTAS,
    DESCRIPCION_TRANSPORTE,
    UNIDAD_POR_DEFECTO,
    calcular_partida,
    codigos_de_partida,
    fcas_nucleo,
    hoja_presupuesto,
    moneda_del_libro,
    parametros_nucleo,
    presupuesto_nucleo,
)
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    MEMORIA,
    D,
    Siembra,
    con,
    construir_libro,
    libro_limpio,
)

A1, A2, A3 = APUS_LIMPIOS


@pytest.fixture(scope="module")
def libro():
    return leer_libro(libro_limpio().datos, "limpio.xlsx")


def _calculo(libro, hoja):
    p = next(p for p in libro.partidas if p.hoja_apu == hoja)
    return calcular_partida(p, libro.apu(hoja), libro, codigos_de_partida(libro)[p.fila])


def _leer(apus, **siembra):
    return leer_libro(construir_libro(apus, Siembra(**siembra)).datos, "variante.xlsx")


# --- Parámetros (F-D1) ---------------------------------------------------------------------------


def test_fcas_de_la_empresa_pasa_al_nucleo_como_fcas_menos_uno(libro):
    assert fcas_nucleo(libro) == D("0.9")
    p = parametros_nucleo(libro.apu("APU-01"), libro)
    assert (p.fcas, p.bono_alimentacion, p.administracion, p.utilidad) == (
        D("0.9"),
        D("0"),
        D("0.1"),
        D("0.1"),
    )


@pytest.mark.parametrize(
    ("fcas", "esperado"),
    [(D("0"), D("0")), (D("1"), D("0")), (D("1.0001"), D("0.0001"))],
)
def test_fcas_frontera_valida(libro, fcas, esperado):
    otro = replace(libro, parametros=replace(libro.parametros, fcas=fcas))
    assert fcas_nucleo(otro) == esperado


@pytest.mark.parametrize("fcas", [D("0.9999"), D("0.5"), D("-1")])
def test_fcas_menor_que_uno_no_se_puede_interpretar(libro, fcas):
    otro = replace(libro, parametros=replace(libro.parametros, fcas=fcas))
    with pytest.raises(LibroNoInterpretable, match=r"El FCAS del libro \(INSUMOS!E16\)"):
        fcas_nucleo(otro)


def test_la_utilidad_es_la_del_apu_aunque_este_escrita_a_mano():
    libro = _leer((A1, con(A2, utilidad_literal=D("0.02")), A3))
    assert parametros_nucleo(libro.apu("APU-02"), libro).utilidad == D("0.02")


# --- El motor reproduce el P.U. de la plantilla --------------------------------------------------


@pytest.mark.parametrize("hoja", ["APU-01", "APU-02", "APU-03"])
def test_motor_reproduce_el_pu_de_la_memoria_exacto(libro, hoja):
    calc = _calculo(libro, hoja)
    m = MEMORIA["componentes"][hoja]
    assert calc.resultado.precio_unitario == m["PU"]
    assert calc.resultado.costo_directo == m["CD"]
    k = calc.calculado
    assert (k.materiales, k.mano_obra, k.equipos, k.transporte) == (
        m["MAT"],
        m["MO"],
        m["EQ"],
        m["TR"],
    )
    assert (k.costo_directo, k.administracion, k.subtotal, k.utilidad) == (
        m["CD"],
        m["ADM"],
        m["SUB"],
        m["UTI"],
    )
    assert k.precio_unitario == m["PU"]
    assert calc.avisos == ()


def test_composicion_de_apu01_con_transporte_y_herramientas_como_lineas(libro):
    """Transporte = LineaMaterial (0,02 m³ a 60 ÷ 6 + 2 = 12 USD/m³); herramientas = LineaEquipo
    de cantidad 1 y precio 0,05 × 35 × 1,9 = 3,325 (el motor lo divide entre 10: 0,3325)."""
    calc = _calculo(libro, "APU-01")
    comp = calc.composicion
    assert [(x.descripcion, x.unidad, x.cantidad, x.precio) for x in comp.materiales] == [
        ("Cemento gris tipo I (ficticio)", "saco", D("0.2"), D("10")),
        ("Arena lavada (ficticia)", "m3", D("0.05"), D("25")),
        (DESCRIPCION_TRANSPORTE, "m3", D("0.02"), D("12")),
    ]
    equipos = [(x.descripcion, x.cantidad, x.precio, x.depreciacion) for x in comp.equipos]
    assert equipos == [
        ("Mezcladora de 1 saco (ficticia)", D("0.5"), D("30"), D("1")),
        (DESCRIPCION_HERRAMIENTAS, D("1"), D("3.325"), D("1")),
    ]
    assert [x.modalidad for x in comp.mano_obra] == [ModalidadManoObra.JORNAL] * 2
    assert (comp.rendimiento, comp.unidad, comp.codigo_partida) == (
        D("10"),
        "m2",
        "E.311.000.001",
    )
    k = calc.calculado
    assert (k.base_mo_dia, k.equipos_dia, k.herramientas) == (D("35"), D("15"), D("0.3325"))


def test_apu_sin_transporte_no_lleva_linea_de_transporte(libro):
    calc = _calculo(libro, "APU-02")
    assert DESCRIPCION_TRANSPORTE not in {x.descripcion for x in calc.composicion.materiales}
    assert calc.calculado.transporte == 0


def test_destajo_entra_completo_sin_fcas_ni_rendimiento():
    """APU-01 con 2 m² de instalador a destajo (MO-03, 3 USD/m²) fuera del subtotal de salarios:
    MO = 35 × 1,9 ÷ 10 + 2 × 3 = 12,65; herramientas = 0,05 × 12,65 = 0,6325; EQ = 1,5 + 0,6325 =
    2,1325; CD = 3,25 + 12,65 + 2,1325 + 0,24 = 18,2725; P.U. = 18,2725 × 1,21 = 22,109725."""
    libro = _leer((con(A1, mano_obra_destajo=(("MO-03", D("2")),)), A2, A3))
    calc = _calculo(libro, "APU-01")
    modalidades = {x.descripcion: x.modalidad for x in calc.composicion.mano_obra}
    assert modalidades["Instalador a destajo (ficticio)"] is ModalidadManoObra.DESTAJO
    assert calc.resultado.mano_obra == D("12.65")
    assert calc.resultado.precio_unitario == D("22.109725")
    # El P.U. del motor coincide con el que guardó la plantilla (sin F1).
    p = next(p for p in libro.partidas if p.hoja_apu == "APU-01")
    assert p.guardados["P"] == D("22.109725")
    assert [a.mensaje for a in calc.avisos] == [
        "MO-03 se paga por m2 (no por día): destajo, entra completo sin FCAS ni rendimiento"
    ]


def test_factor_escrito_en_la_formula_de_la_linea_se_conserva():
    """`=E10*F10*1.1` en MT-01 de APU-01 (RL-8): MAT = 0,2 × 10 × 1,1 + 1,25 = 3,45;
    CD = 3,45 + 6,65 + 1,8325 + 0,24 = 12,1725; P.U. = 12,1725 × 1,21 = 14,728725."""
    libro = _leer((con(A1, factores={"MT-01": "*1.1"}), A2, A3))
    calc = _calculo(libro, "APU-01")
    assert calc.resultado.precio_unitario == D("14.728725")
    assert calc.composicion.materiales[0].cantidad == D("0.22")
    assert len(calc.avisos) == 1
    assert calc.avisos[0].origen == "APU-01!G10"
    assert "multiplica cantidad × precio por 1.1" in calc.avisos[0].mensaje


def test_factor_divisor_en_un_equipo():
    """`=E25*F25/8` en EQ-01: equipos/día = 0,5 × 30 ÷ 8 = 1,875; EQ = 1,875 ÷ 10 + 0,3325 =
    0,52; CD = 3,25 + 6,65 + 0,52 + 0,24 = 10,66; P.U. = 10,66 × 1,21 = 12,8986."""
    libro = _leer((con(A1, factores={"EQ-01": "/8"}), A2, A3))
    calc = _calculo(libro, "APU-01")
    assert calc.resultado.precio_unitario == D("12.8986")
    assert calc.calculado.equipos_dia == D("1.875")


def test_divisor_literal_de_equipos_distinto_del_rendimiento_se_conserva():
    """`=G26/12+G27` (H12, F-D7): EQ = 15 ÷ 12 + 0,3325 = 1,5825; CD = 11,7225;
    P.U. = 11,7225 × 1,21 = 14,184225."""
    libro = _leer((con(A1, divisor_equipos=D("12")), A2, A3))
    calc = _calculo(libro, "APU-01")
    assert calc.resultado.equipos == D("1.5825")
    assert calc.resultado.precio_unitario == D("14.184225")
    assert [a.origen for a in calc.avisos] == ["APU-01!G28"]
    assert "se dividen entre 12 y no entre el rendimiento (10)" in calc.avisos[0].mensaje


def test_divisor_igual_al_rendimiento_no_avisa():
    libro = _leer((con(A1, divisor_equipos=D("10")), A2, A3))
    calc = _calculo(libro, "APU-01")
    assert calc.resultado.precio_unitario == MEMORIA["componentes"]["APU-01"]["PU"]
    assert calc.avisos == ()


def test_codigo_que_no_esta_en_insumos_usa_el_precio_del_apu():
    libro = _leer(
        APUS_LIMPIOS,
        parches={"APU-01!B10": ("MT-99", None), "APU-01!F10": (D("10"), None)},
    )
    calc = _calculo(libro, "APU-01")
    assert calc.resultado.precio_unitario == MEMORIA["componentes"]["APU-01"]["PU"]
    assert [(a.origen, a.mensaje) for a in calc.avisos][0] == (
        "APU-01!B10",
        "MT-99 no está en INSUMOS: se usa el precio que muestra el APU (10)",
    )


def test_el_precio_sale_de_insumos_y_no_del_apu():
    """Si la línea del APU muestra un precio viejo (12) y INSUMOS dice 10, el motor usa 10."""
    libro = _leer(APUS_LIMPIOS, parches={"APU-01!F10": (D("12"), "=VLOOKUP(B10,PRECIOS,4,0)")})
    assert libro.apu("APU-01").lineas[0].precio == D("12")
    calc = _calculo(libro, "APU-01")
    assert calc.resultado.precio_unitario == MEMORIA["componentes"]["APU-01"]["PU"]


def test_sin_unidad_en_el_libro_usa_la_de_respaldo_y_avisa():
    libro = _leer(APUS_LIMPIOS, parches={"APU-01!B5": (None, None), "PRESUPUESTO!E5": (None, None)})
    calc = _calculo(libro, "APU-01")
    # El contrato del núcleo normaliza la unidad («und» -> «unidad»).
    assert calc.composicion.unidad == normalizar_unidad(UNIDAD_POR_DEFECTO) == "unidad"
    assert ("APU-01!unidad", f"sin unidad en el libro: se usa «{UNIDAD_POR_DEFECTO}»") in {
        (a.origen, a.mensaje) for a in calc.avisos
    }


def test_rendimiento_cero_no_se_puede_calcular():
    """El docstring de `calcular_partida` dice que el rendimiento 0 lo rechaza el contrato
    (`ValueError`); en realidad cae antes, al dividir las herramientas (`DivisionByZero`, un
    `ArithmeticError`). `fusion.proceso` traduce las dos a `LibroNoInterpretable` (ver
    test_fusion_proceso)."""
    libro = _leer(APUS_LIMPIOS, parches={"APU-01!F19": (D("0"), None)})
    with pytest.raises((ValueError, ArithmeticError)):
        _calculo(libro, "APU-01")


# --- Códigos, moneda y presupuesto del núcleo ----------------------------------------------------


def test_codigos_unicos_de_partida():
    """Código vacío o «S/C» -> P<número>; código repetido -> <código>#<fila>."""
    apus = (con(A1, codigo="S/C"), con(A2, codigo="E.1"), con(A3, codigo="E.1"))
    libro = _leer(apus)
    assert codigos_de_partida(libro) == {5: "P1", 6: "E.1#6", 7: "E.1#7"}


@pytest.mark.parametrize(
    ("texto", "moneda"),
    [
        ("Dólares de los Estados Unidos de América (USD)", "USD"),
        ("Bolívares (Bs)", "Bs"),
        ("BOLIVAR DIGITAL", "Bs"),
        ("VES", "Bs"),
        ("Bs.", "Bs"),
        ("Bsx", "USD"),  # «bs» pegado a otras letras no es la moneda
        ("", "USD"),
    ],
)
def test_moneda_del_libro(libro, texto, moneda):
    otro = replace(libro, portada=Portada(moneda=texto))
    assert moneda_del_libro(otro) == moneda


def test_presupuesto_del_nucleo_trazable_por_celda(libro):
    calculos = [_calculo(libro, h) for h in ("APU-01", "APU-02", "APU-03")]
    pres = presupuesto_nucleo(libro, calculos, date(2026, 7, 31))
    assert (pres.codigo, pres.fecha, pres.moneda) == ("limpio.xlsx", date(2026, 7, 31), "USD")
    assert [
        (p.item.codigo_partida, p.item.cantidad, p.item.origen_id, p.item.origen_tipo)
        for p in pres.partidas
    ] == [
        ("E.311.000.001", D("120"), "PRESUPUESTO!G5", OrigenTipo.TABULAR),
        ("E.321.000.002", D("80"), "PRESUPUESTO!G6", OrigenTipo.TABULAR),
        ("E.041.000.003", D("50"), "PRESUPUESTO!G7", OrigenTipo.TABULAR),
    ]
    total = sum((p.item.cantidad * p.resultado.precio_unitario for p in pres.partidas), Decimal(0))
    assert total == MEMORIA["SUBSINIVA"]
    assert hoja_presupuesto(libro) == "PRESUPUESTO"
