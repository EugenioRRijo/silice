"""Funciones puras de composición (Sesión P2.1).

Lo único verificable antes de que existan pruebas de interfaz es lo que se puede llamar sin
Streamlit (spec §4). Estas pruebas fijan ese contorno.
"""

from decimal import Decimal

import pytest

from core.contracts import Dominio, ModalidadManoObra, OrigenTipo, ParametrosCosto
from core.costing import calcular_apu
from tests.fixtures.apu_linea_base import APU_TUBERIA, PRECIO_UNITARIO_ESPERADO
from ui.composicion import (
    ComposicionInvalida,
    FilaReferencia,
    buscar_referencia,
    composicion_desde_tablas,
    decimal_desde_texto,
    desglose,
    fila_equipos_desde_referencia,
    fila_mano_obra_desde_referencia,
    fila_materiales_desde_referencia,
    filas_desde_composicion,
    item_desde_cantidad,
    motivo_para_no_reemplazar,
)

MATERIALES = [{"descripcion": "Cemento", "unidad": "saco", "cantidad": "7.5", "precio": "8.00"}]
EQUIPOS = [{"descripcion": "Vibrador", "cantidad": "1", "precio": "300.00", "depreciacion": "0.03"}]
MANO_OBRA = [
    {"descripcion": "Obrero de primera", "cantidad": "2", "sueldo": "12.50", "modalidad": "jornal"},
    {"descripcion": "Friso", "cantidad": "1", "sueldo": "6.00", "modalidad": "destajo"},
]


def test_una_tabla_valida_produce_la_composicion_esperada():
    composicion = composicion_desde_tablas(
        "LB-04-VAC", "Vaciado de concreto", "m3", "8", MATERIALES, EQUIPOS, MANO_OBRA
    )

    assert composicion.codigo_partida == "LB-04-VAC"
    assert composicion.rendimiento == Decimal("8")
    assert composicion.materiales[0].cantidad == Decimal("7.5")
    assert composicion.equipos[0].depreciacion == Decimal("0.03")
    assert composicion.mano_obra[1].modalidad is ModalidadManoObra.DESTAJO
    assert composicion.total_obreros == Decimal("2"), "el destajista no cuenta para el bono"


def test_una_cantidad_no_numerica_nombra_el_campo_culpable():
    filas = [{"descripcion": "Cemento", "unidad": "saco", "cantidad": "siete", "precio": "8.00"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert "cantidad" in str(error.value)
    assert "Cemento" in str(error.value)


def test_las_filas_vacias_se_descartan():
    filas = MATERIALES + [{"descripcion": "  ", "unidad": "", "cantidad": "", "precio": ""}]

    composicion = composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert len(composicion.materiales) == 1


def test_un_rendimiento_cero_o_negativo_se_rechaza():
    for valor in ("0", "-3"):
        with pytest.raises(ComposicionInvalida, match="rendimiento"):
            composicion_desde_tablas("P-01", "Prueba", "m3", valor, MATERIALES, [], MANO_OBRA)


def test_la_unidad_con_alias_se_normaliza():
    composicion = composicion_desde_tablas("P-01", "Prueba", "m³", "8", MATERIALES, [], MANO_OBRA)

    assert composicion.unidad == "m3"


def test_una_modalidad_desconocida_se_rechaza_nombrando_la_fila():
    filas = [{"descripcion": "Friso", "cantidad": "1", "sueldo": "6.00", "modalidad": "por pieza"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", MATERIALES, [], filas)

    assert "Friso" in str(error.value)
    assert "modalidad" in str(error.value)


def test_una_fila_de_mano_de_obra_sin_modalidad_es_jornal():
    filas = [{"descripcion": "Obrero", "cantidad": "1", "sueldo": "12.50"}]

    composicion = composicion_desde_tablas("P-01", "Prueba", "m3", "8", MATERIALES, [], filas)

    assert composicion.mano_obra[0].modalidad is ModalidadManoObra.JORNAL


def test_item_desde_cantidad_es_trazable_y_manual():
    item = item_desde_cantidad(
        "LB-04-VAC",
        "Vaciado de concreto",
        "m3",
        "1.66",
        "memoria de calculo 2026-09",
        Dominio.CIVIL,
    )

    assert item.origen_tipo is OrigenTipo.MANUAL
    assert item.cantidad == Decimal("1.66")
    assert item.origen_id == "memoria de calculo 2026-09"


def test_item_desde_cantidad_exige_origen():
    with pytest.raises(ComposicionInvalida, match="origen"):
        item_desde_cantidad("LB-04-VAC", "Vaciado", "m3", "1.66", "   ", Dominio.CIVIL)


def test_decimal_desde_texto_rechaza_lo_que_no_es_finito():
    assert decimal_desde_texto(" 7.5 ", "cantidad") == Decimal("7.5")
    with pytest.raises(ComposicionInvalida, match="cantidad"):
        decimal_desde_texto("Infinity", "cantidad")


# --- Hallazgo 2.1: los errores del contrato deben nombrar la tabla y la fila culpables ---------


def test_una_cantidad_negativa_en_la_segunda_fila_nombra_la_tabla_y_la_fila():
    filas = [
        {"descripcion": "Cemento", "unidad": "saco", "cantidad": "7.5", "precio": "8.00"},
        {"descripcion": "Arena", "unidad": "saco", "cantidad": "-5", "precio": "3.00"},
    ]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert "materiales, fila 2" in str(error.value)
    assert "no puede ser negativo" in str(error.value)


def test_una_depreciacion_fuera_de_rango_nombra_la_tabla_equipos():
    filas = [
        {"descripcion": "Vibrador", "cantidad": "1", "precio": "300.00", "depreciacion": "1.5"}
    ]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", [], filas, MANO_OBRA)

    assert "equipos, fila 1" in str(error.value)
    assert "depreciacion debe estar en" in str(error.value)


def test_una_unidad_vacia_en_una_fila_se_distingue_de_la_unidad_vacia_de_la_partida():
    fila_sin_unidad = [
        {"descripcion": "Cemento", "unidad": "  ", "cantidad": "7.5", "precio": "8.00"}
    ]

    with pytest.raises(ComposicionInvalida) as error_de_fila:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", fila_sin_unidad, [], MANO_OBRA)
    with pytest.raises(ComposicionInvalida) as error_de_partida:
        composicion_desde_tablas("P-01", "Prueba", "  ", "8", MATERIALES, [], MANO_OBRA)

    assert "materiales, fila 1" in str(error_de_fila.value)
    assert "materiales" not in str(error_de_partida.value)
    assert "La unidad no puede estar vac" in str(error_de_fila.value)
    assert "La unidad no puede estar vac" in str(error_de_partida.value)


# --- Hallazgo 2.2: una fila con datos pero sin descripcion se rechaza --------------------------


def test_una_fila_de_materiales_con_datos_pero_sin_descripcion_se_rechaza():
    filas = [{"descripcion": "   ", "unidad": "saco", "cantidad": "7.5", "precio": "8.00"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert "materiales, fila 1" in str(error.value)
    assert "descripcion" in str(error.value)


def test_una_fila_de_equipos_con_datos_pero_sin_descripcion_se_rechaza():
    filas = [{"descripcion": "", "cantidad": "1", "precio": "300.00", "depreciacion": "0.03"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", [], filas, MANO_OBRA)

    assert "equipos, fila 1" in str(error.value)
    assert "descripcion" in str(error.value)


def test_una_fila_de_mano_de_obra_con_datos_pero_sin_descripcion_se_rechaza():
    filas = [{"descripcion": "", "cantidad": "1", "sueldo": "12.50", "modalidad": "jornal"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", MATERIALES, [], filas)

    assert "mano de obra, fila 1" in str(error.value)
    assert "descripcion" in str(error.value)


# --- Hallazgo 2.3: `None` y NaN de `st.data_editor` se normalizan a vacio -----------------------


def test_una_fila_con_none_en_todas_las_celdas_se_descarta_como_vacia():
    filas = [{"descripcion": None, "unidad": None, "cantidad": None, "precio": None}]

    composicion = composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert composicion.materiales == ()


def test_una_fila_con_nan_en_todas_las_celdas_se_descarta_como_vacia():
    filas = [{"descripcion": "nan", "unidad": "NaN", "cantidad": "nan", "precio": "NaN"}]

    composicion = composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert composicion.materiales == ()


def test_una_fila_con_none_solo_en_cantidad_nombra_la_fila_no_el_texto_none():
    filas = [{"descripcion": "Cemento", "unidad": "saco", "cantidad": None, "precio": "8.00"}]

    with pytest.raises(ComposicionInvalida) as error:
        composicion_desde_tablas("P-01", "Prueba", "m3", "8", filas, [], MANO_OBRA)

    assert "None" not in str(error.value)
    assert "cantidad (Cemento)" in str(error.value)


# --- Tarea 2: busqueda en la referencia MaPreX, como funcion pura ------------------------------
#
# Filas reales de `data/precios/maprex_2026-07/referencia_civil.csv` (no inventadas), elegidas
# porque cubren los cinco casos del brief con datos ya presentes en el archivo:
# - CEM019 "CEMENTO GRIS PORTLAND SACO 42.5 KG/93,7 LB" (material): sin factor_depreciacion ni
#   bono_bs.
# - MOV027 "RETROEXCAVADORA CASE O SIM" (equipo): con factor_depreciacion, sin bono_bs.
# - 19-2.2 "ALBAÑIL DE 1RA -N5" (mano_obra): con bono_bs, sin factor_depreciacion; sirve ademas
#   para probar mayusculas y acentos porque su descripcion lleva una eñe.


def test_buscar_referencia_encuentra_la_fila_esperada_con_ref_y_precio_decimal():
    resultados = buscar_referencia("cemento gris portland", "material")

    assert len(resultados) == 1
    fila = resultados[0]
    assert isinstance(fila, FilaReferencia)
    assert fila.descripcion == "CEMENTO GRIS PORTLAND SACO 42.5 KG/93,7 LB"
    assert fila.ref_maprex == "CEM019"
    assert fila.precio_usd == Decimal("19.0727")
    assert type(fila.precio_usd) is Decimal


def test_buscar_referencia_sin_coincidencias_devuelve_lista_vacia():
    resultados = buscar_referencia("insumo que no existe en ningun listado", "material")

    assert resultados == []


def test_buscar_referencia_es_insensible_a_mayusculas_y_acentos():
    resultados = buscar_referencia("ALBANIL", "mano_obra")

    assert len(resultados) == 1
    assert resultados[0].descripcion == "ALBAÑIL DE 1RA -N5"
    assert resultados[0].ref_maprex == "19-2.2"


def test_buscar_referencia_factor_depreciacion_solo_lleno_en_equipos():
    equipo = buscar_referencia("retroexcavadora", "equipo")[0]
    material = buscar_referencia("cemento gris portland", "material")[0]

    assert equipo.factor_depreciacion == Decimal("0.003500")
    assert type(equipo.factor_depreciacion) is Decimal
    assert material.factor_depreciacion is None


def test_buscar_referencia_todo_numero_es_decimal_construido_desde_texto():
    mano_obra = buscar_referencia("albanil", "mano_obra")[0]

    assert mano_obra.bono_bs == Decimal("3679.85")
    assert type(mano_obra.bono_bs) is Decimal
    assert type(mano_obra.precio_usd) is Decimal
    assert mano_obra.factor_depreciacion is None


def test_el_precio_sugerido_por_la_referencia_es_editable_y_el_calculo_lo_refleja():
    """RF‑35: la referencia MaPreX sugiere, nunca decide (spec §3.4). `fila_materiales_desde_
    referencia`/`fila_equipos_desde_referencia`/`fila_mano_obra_desde_referencia` solo proponen el
    precio como texto de la celda; si la persona lo cambia antes de guardar,
    `composicion_desde_tablas` acepta la fila con el precio nuevo y `core.costing.calcular_apu` lo
    refleja, no el sugerido.
    """
    referencia_material = FilaReferencia(
        tipo="material",
        descripcion="Cemento",
        unidad="saco",
        precio_usd=Decimal("8.00"),
        factor_depreciacion=None,
        bono_bs=None,
        ref_maprex="REF-MAT",
    )
    referencia_equipo = FilaReferencia(
        tipo="equipo",
        descripcion="Vibrador",
        unidad="dia",
        precio_usd=Decimal("300.00"),
        factor_depreciacion=Decimal("0.03"),
        bono_bs=None,
        ref_maprex="REF-EQU",
    )
    referencia_mano_obra = FilaReferencia(
        tipo="mano_obra",
        descripcion="Albanil",
        unidad="jornal",
        precio_usd=Decimal("12.50"),
        factor_depreciacion=None,
        bono_bs=Decimal("1.00"),
        ref_maprex="REF-MO",
    )

    fila_material = fila_materiales_desde_referencia(referencia_material)
    fila_equipo = fila_equipos_desde_referencia(referencia_equipo)
    fila_mano_obra = fila_mano_obra_desde_referencia(referencia_mano_obra)

    # El precio sugerido llega como texto de la celda (no como Decimal, no de solo lectura): sigue
    # siendo el mismo campo que la persona puede teclear encima, igual que si lo hubiera escrito.
    assert fila_material["precio"] == "8.00"
    assert fila_equipo["precio"] == "300.00"
    assert fila_mano_obra["sueldo"] == "12.50"
    assert all(
        isinstance(valor, str)
        for valor in (fila_material["precio"], fila_equipo["precio"], fila_mano_obra["sueldo"])
    )

    # La persona edita las tres celdas de precio antes de guardar (y completa la cantidad, que la
    # referencia no sugiere: spec §3.4, solo describe el insumo, no cuanto se usa).
    fila_material = {**fila_material, "cantidad": "2", "precio": "9.50"}
    fila_equipo = {**fila_equipo, "cantidad": "1", "precio": "320.00"}
    fila_mano_obra = {**fila_mano_obra, "cantidad": "1", "sueldo": "15.00", "modalidad": "jornal"}

    composicion = composicion_desde_tablas(
        "P-RF35",
        "Prueba de editabilidad del precio sugerido",
        "m3",
        "10",
        [fila_material],
        [fila_equipo],
        [fila_mano_obra],
    )

    # La fila se acepta con el precio nuevo, no con el sugerido.
    assert composicion.materiales[0].precio == Decimal("9.50")
    assert composicion.equipos[0].precio == Decimal("320.00")
    assert composicion.mano_obra[0].sueldo == Decimal("15.00")

    resultado = calcular_apu(composicion, ParametrosCosto())

    # Si `composicion_desde_tablas` hubiera ignorado la edicion y colado el precio sugerido
    # (8.00 USD/saco), el resultado seria 16.00, no 19.00: afirmar primero el sugerido hace fallar
    # esta prueba, lo que demuestra que el campo es editable de verdad, no de solo lectura.
    assert resultado.materiales == Decimal("19.00")
    assert resultado.materiales != Decimal("2") * referencia_material.precio_usd


# --- UC-11: guarda antes de reemplazar y precarga de las tres tablas (auditoria del PR #7) -------

#: La partida "registrada" de estas pruebas: la de `test_una_tabla_valida_...`, ya en el catalogo.
DESCRIPCION_REGISTRADA = "Vaciado de concreto"
UNIDAD_REGISTRADA = "m3"


def _edicion(
    descripcion=DESCRIPCION_REGISTRADA,
    unidad=UNIDAD_REGISTRADA,
    materiales=MATERIALES,
    equipos=EQUIPOS,
    mano_obra=MANO_OBRA,
):
    return composicion_desde_tablas(
        "LB-04-VAC", descripcion, unidad, "8", materiales, equipos, mano_obra
    )


def test_una_edicion_con_la_misma_cabecera_y_lineas_se_puede_reemplazar():
    assert motivo_para_no_reemplazar(DESCRIPCION_REGISTRADA, UNIDAD_REGISTRADA, _edicion()) is None


def test_una_edicion_sin_ninguna_linea_no_reemplaza():
    motivo = motivo_para_no_reemplazar(
        DESCRIPCION_REGISTRADA,
        UNIDAD_REGISTRADA,
        _edicion(materiales=[], equipos=[], mano_obra=[]),
    )

    assert motivo is not None
    assert "LB-04-VAC" in motivo
    assert "ninguna linea" in motivo


def test_basta_una_linea_en_cualquiera_de_las_tres_tablas():
    solo_mano_obra = _edicion(materiales=[], equipos=[])

    motivo = motivo_para_no_reemplazar(DESCRIPCION_REGISTRADA, UNIDAD_REGISTRADA, solo_mano_obra)

    assert motivo is None


def test_otra_unidad_no_reemplaza_y_dice_la_registrada():
    motivo = motivo_para_no_reemplazar(
        DESCRIPCION_REGISTRADA, UNIDAD_REGISTRADA, _edicion(unidad="m2")
    )

    assert motivo is not None
    assert "'m3'" in motivo


def test_una_unidad_equivalente_no_es_otra_unidad():
    """`m³` y `m3` son la misma unidad (`core.contracts.unidades`), no un cambio de cabecera."""
    assert motivo_para_no_reemplazar(DESCRIPCION_REGISTRADA, "m³", _edicion(unidad="m3")) is None


def test_otra_descripcion_no_reemplaza_y_dice_la_registrada():
    motivo = motivo_para_no_reemplazar(
        DESCRIPCION_REGISTRADA, UNIDAD_REGISTRADA, _edicion(descripcion="Vaciado de losa")
    )

    assert motivo is not None
    assert f"'{DESCRIPCION_REGISTRADA}'" in motivo


def test_los_espacios_de_borde_de_la_descripcion_no_son_otra_descripcion():
    edicion = _edicion(descripcion=f"  {DESCRIPCION_REGISTRADA} ")

    assert motivo_para_no_reemplazar(DESCRIPCION_REGISTRADA, UNIDAD_REGISTRADA, edicion) is None


def test_filas_desde_composicion_es_la_ida_y_vuelta_de_composicion_desde_tablas():
    """Precargar las tablas (UC-11, paso 1) y volver a leerlas reproduce la misma composicion."""
    composicion = _edicion()

    materiales, equipos, mano_obra = filas_desde_composicion(composicion)

    assert mano_obra[1]["modalidad"] == "destajo"
    celdas = [valor for fila in materiales + equipos + mano_obra for valor in fila.values()]
    assert all(isinstance(valor, str) for valor in celdas)
    assert (
        composicion_desde_tablas(
            composicion.codigo_partida,
            composicion.descripcion,
            composicion.unidad,
            "8",
            materiales,
            equipos,
            mano_obra,
        )
        == composicion
    )


def test_filas_desde_composicion_escribe_los_decimales_sin_exponente():
    composicion = _edicion(
        equipos=[
            {"descripcion": "Vibrador", "cantidad": "1E+2", "precio": "300", "depreciacion": "1"}
        ]
    )

    _, (equipo,), _ = filas_desde_composicion(composicion)

    assert equipo["cantidad"] == "100"


def test_desglose_de_la_tuberia_da_el_precio_de_la_linea_base():
    """INV-043 (11c): el desglose en vivo sale de la pagina. Oraculo: NORMAS.md §4 y la fixture
    (costo directo 8,058; PU 10,19 a dos decimales)."""
    resultado = desglose(APU_TUBERIA)
    assert resultado.costo_directo == Decimal("8.058")
    assert (
        resultado.precio_unitario.quantize(Decimal("0.01")) == PRECIO_UNITARIO_ESPERADO["LB-02-TUB"]
    )
