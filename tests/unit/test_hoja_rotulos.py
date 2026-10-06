"""Rotulos en espanol de las tablas de la hoja y resumen honesto de la fusion (revision final, H).

Las tablas editables mostraban los nombres internos (`montante_agua`, `agua_fria`, `ambiente_id`):
RNF-13 las mide con personas, que no tienen por que conocerlos. La logica de los rotulos vive en
`ui.hoja` (sin Streamlit); la pantalla los pone con `column_config` sin cambiar los datos ni los
nombres internos de las columnas del `st.data_editor`.

El informe de la ultima fusion contaba el informe de la importacion MAS una linea «agregada» por
fila que la fusion agrego: por eso mostraba Importado 68 y no 33. Aqui se prueba el resumen que
cuenta cada cosa una vez: lo que leyo el plano, las filas por tabla y los origenes aparte.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from adapters.espacio import Espacio
from adapters.espacio.modelo import (
    Especialidad,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import TipoOrigen
from ui import hoja

DXF = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "planos" / "of001.dxf"


def _borrador() -> hoja.Borrador:
    return hoja.Borrador(fecha=date(2026, 10, 5), espacio=Espacio())


# --- rotulos de columna -------------------------------------------------------------------------


def test_cada_columna_editable_tiene_su_rotulo_en_espanol_sin_nombres_internos():
    assert set(hoja.ROTULOS_DE_COLUMNA) == set(hoja.COLUMNAS)
    for tabla, columnas in hoja.COLUMNAS.items():
        rotulos = hoja.ROTULOS_DE_COLUMNA[tabla]
        assert set(rotulos) == set(columnas), tabla
        for columna, rotulo in rotulos.items():
            assert rotulo and "_" not in rotulo, (tabla, columna, rotulo)
            assert rotulo[0].isupper(), (tabla, columna, rotulo)
        assert len(set(rotulos.values())) == len(rotulos), f"rotulos repetidos en {tabla}"


# --- rotulos de valor ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "enum", [TipoOrigen, Especialidad, TipoFuente, TipoPunto, SuperficiePunto, SuperficieTramo]
)
def test_cada_valor_de_lista_cerrada_tiene_un_rotulo_claro(enum):
    for miembro in enum:
        rotulo = hoja.rotulo_de_valor(miembro.value)
        assert rotulo and "_" not in rotulo, (miembro.value, rotulo)
        assert rotulo[0].isupper(), (miembro.value, rotulo)


def test_los_valores_que_el_usuario_ve_son_los_del_ejemplo_del_encargo():
    assert hoja.rotulo_de_valor("montante_agua") == "Montante de agua fría"
    assert hoja.rotulo_de_valor("agua_fria") == "Agua fría"
    assert hoja.ROTULOS_DE_COLUMNA["fuentes"]["ambiente_id"] == "Ambiente"


def test_un_valor_sin_rotulo_se_muestra_tal_cual_y_el_vacio_no_revienta():
    assert hoja.rotulo_de_valor("lo-que-sea") == "lo-que-sea"
    assert hoja.rotulo_de_valor("") == ""


def test_los_rotulos_no_cambian_los_datos_ni_los_nombres_internos():
    """El editor sigue entregando los valores internos: el rotulo es solo de pantalla."""
    base = hoja.filas_desde_espacio(Espacio())
    assert set(base) == set(hoja.COLUMNAS)
    assert hoja.COLUMNAS["fuentes"][3] == "ambiente_id"
    assert TipoFuente.MONTANTE_AGUA.value == "montante_agua"


# --- resumen de la fusion -----------------------------------------------------------------------


def test_el_resumen_de_la_fusion_cuenta_cada_cosa_una_vez():
    resultado = hoja.leer_plano(DXF)
    _, informe = hoja.fusionar_plano(_borrador(), resultado)
    resumen = hoja.resumen_de_la_fusion(resultado, informe)

    # lo que leyo el plano: 33 filas importadas (6 ambientes + 6 fuentes + 21 puntos), no 68
    assert dict(resumen.por_tipo)["Importado"] == 33
    assert dict(resumen.por_tipo)["Pendiente"] == 6
    # lo que la fusion agrego al borrador, por tabla, y los origenes aparte
    assert resumen.filas_por_tabla == [
        ("Ambientes", 6),
        ("Fuentes", 6),
        ("Puntos", 21),
        ("Circuitos", 2),
    ]
    assert resumen.origenes == len(resultado.origenes)
    # el total de filas es la suma de la tabla, sin sumar los origenes ni el informe doble
    assert sum(n for _, n in resumen.filas_por_tabla) == 35
    assert sum(n for _, n in resumen.por_tipo) != len(informe)


def test_reimportar_el_mismo_plano_no_vuelve_a_contar_lo_que_ya_estaba():
    resultado = hoja.leer_plano(DXF)
    borrador, _ = hoja.fusionar_plano(_borrador(), resultado)
    _, informe = hoja.fusionar_plano(borrador, resultado)
    resumen = hoja.resumen_de_la_fusion(resultado, informe)
    assert dict(resumen.por_tipo)["Importado"] == 33
    assert [t for t, _ in resumen.filas_por_tabla] == ["Ambientes", "Fuentes", "Puntos"]
