"""Detector de columnas del reporte de bascula (Tarea 4.6, RT-S4-5 y RT-S4-6).

Todo es EJEMPLO CONSTRUIDO: los sinonimos de encabezado son un supuesto declarado (PLAN_FUENTES C-8)
y solo se prueban con encabezados escritos aqui. Los valores esperados estan a mano, no salen del codigo.
"""

from __future__ import annotations

import pytest

from produccion.conectores.detector_columnas import (
    CAMPOS,
    MapeoColumnas,
    MapeoNecesario,
    detectar,
)
from produccion.fuentes import FILAS_DE_ENCABEZADO

ENCABEZADO_BASICO = [
    "Ticket",
    "Fecha",
    "Placa",
    "Cliente",
    "Material",
    "Bruto (kg)",
    "Tara (kg)",
    "Neto (kg)",
]
FILA_DE_DATOS = ["TCK-001", "2026-10-15", "EJ-001", "Cliente Ejemplo A", "ARENA", 42500, 14200, 28300]


def test_los_campos_son_los_ocho_del_plan():
    assert CAMPOS == ("ticket", "fecha", "placa", "cliente", "material", "bruto", "tara", "neto")


def test_detecta_las_ocho_columnas_del_reporte_basico():
    mapeo = detectar([ENCABEZADO_BASICO, FILA_DE_DATOS])
    assert mapeo == MapeoColumnas(
        columnas={
            "ticket": 0,
            "fecha": 1,
            "placa": 2,
            "cliente": 3,
            "material": 4,
            "bruto": 5,
            "tara": 6,
            "neto": 7,
        },
        fila_encabezado=0,
        unidad_peso="kg",
    )


def test_sinonimos_de_encabezado():
    # `Boleto`, `N° Ticket`, `Placa del camión`, `Peso Neto (t)` (plan 4.6, Step 1).
    con_boleto = detectar([["Boleto", "Fecha", "Material", "Peso Neto (t)"]])
    assert con_boleto.columnas == {"ticket": 0, "fecha": 1, "material": 2, "neto": 3}
    assert con_boleto.unidad_peso == "t"

    con_numero = detectar(
        [["N° Ticket", "FECHA", "Placa del camión", "Cliente", "Material", "Peso Neto (t)"]]
    )
    assert con_numero.columnas == {
        "ticket": 0,
        "fecha": 1,
        "placa": 2,
        "cliente": 3,
        "material": 4,
        "neto": 5,
    }
    assert con_numero.unidad_peso == "t"


def test_encabezados_sin_tildes_ni_signos_ni_mayusculas():
    mapeo = detectar([["  TICKET: ", "Fecha.", "MATERIAL", "Peso   Neto   (Kg)"]])
    assert mapeo.columnas == {"ticket": 0, "fecha": 1, "material": 2, "neto": 3}
    assert mapeo.unidad_peso == "kg"
    otro = detectar([["Número de Ticket", "Fecha de Pesaje", "Producto", "Neto"]])
    assert otro.columnas == {"ticket": 0, "fecha": 1, "material": 2, "neto": 3}


@pytest.mark.parametrize(
    ("peso", "unidad"),
    [
        ("Neto (kg)", "kg"),
        ("Neto kg", "kg"),
        ("Neto (Kilos)", "kg"),
        ("Neto (ton)", "t"),
        ("Neto (t)", "t"),
        ("Neto toneladas", "t"),
        ("Neto", None),
    ],
)
def test_unidad_del_encabezado_del_peso(peso, unidad):
    assert detectar([["Ticket", "Fecha", "Material", peso]]).unidad_peso == unidad


def test_unidades_contradictorias_entre_encabezados_no_se_adivinan():
    mapeo = detectar([["Ticket", "Fecha", "Material", "Bruto (kg)", "Tara (kg)", "Neto (t)"]])
    assert mapeo.unidad_peso is None


def test_faltan_columnas_pide_mapeo():
    sin_material = [e for e in ENCABEZADO_BASICO if e != "Material"]
    with pytest.raises(MapeoNecesario) as error:
        detectar([sin_material])
    assert error.value.faltan == ("material",)
    assert isinstance(error.value, ValueError)


def test_faltan_varias_columnas_en_el_orden_de_campos():
    with pytest.raises(MapeoNecesario) as error:
        detectar([["Placa", "Cliente", "Neto (kg)"]])
    assert error.value.faltan == ("ticket", "fecha", "material")


def test_sin_neto_sirven_bruto_y_tara():
    mapeo = detectar([["Ticket", "Fecha", "Material", "Bruto (kg)", "Tara (kg)"]])
    assert mapeo.columnas == {"ticket": 0, "fecha": 1, "material": 2, "bruto": 3, "tara": 4}


def test_sin_neto_y_con_un_solo_peso_falta_el_otro():
    with pytest.raises(MapeoNecesario) as error:
        detectar([["Ticket", "Fecha", "Material", "Bruto (kg)"]])
    assert error.value.faltan == ("tara",)
    with pytest.raises(MapeoNecesario) as error:
        detectar([["Ticket", "Fecha", "Material", "Tara (kg)"]])
    assert error.value.faltan == ("bruto",)


def test_sin_ningun_peso_falta_el_neto():
    with pytest.raises(MapeoNecesario) as error:
        detectar([["Ticket", "Fecha", "Material"]])
    assert error.value.faltan == ("neto",)


def test_sin_filas_o_sin_encabezado_reconocible_pide_todo():
    with pytest.raises(MapeoNecesario) as vacio:
        detectar([])
    assert vacio.value.faltan == ("ticket", "fecha", "material", "neto")
    with pytest.raises(MapeoNecesario) as raro:
        detectar([["Col A", "Col B", "Col C"]])
    assert raro.value.faltan == ("ticket", "fecha", "material", "neto")


def test_el_encabezado_puede_no_ser_la_primera_fila():
    titulo = ["Reporte de pesajes (ejemplo construido)", None, None]
    mapeo = detectar([titulo, [], ENCABEZADO_BASICO, FILA_DE_DATOS])
    assert mapeo.fila_encabezado == 2
    assert mapeo.columnas["neto"] == 7


def test_el_encabezado_se_busca_solo_en_las_filas_iniciales():
    relleno = [["texto"]] * (FILAS_DE_ENCABEZADO - 1)
    ultima_admitida = detectar([*relleno, ENCABEZADO_BASICO])
    assert ultima_admitida.fila_encabezado == FILAS_DE_ENCABEZADO - 1
    with pytest.raises(MapeoNecesario):
        detectar([*relleno, ["texto"], ENCABEZADO_BASICO])


def test_celdas_que_no_son_texto_no_rompen_el_detector():
    fila = [None, 3, 4.5, "Ticket", "Fecha", "Material", "Neto (kg)"]
    mapeo = detectar([fila])
    assert mapeo.columnas == {"ticket": 3, "fecha": 4, "material": 5, "neto": 6}


def test_una_columna_no_se_asigna_a_dos_campos_ni_un_campo_a_dos_columnas():
    mapeo = detectar([["Ticket", "Boleto", "Fecha", "Material", "Neto (kg)"]])
    assert mapeo.columnas["ticket"] == 0  # la primera columna que coincide


def test_gana_la_fila_con_mas_campos_reconocidos():
    pobre = ["Fecha", "Notas"]
    rica = ["Ticket", "Fecha", "Material", "Neto (kg)"]
    mapeo = detectar([pobre, rica])
    assert mapeo.fila_encabezado == 1
