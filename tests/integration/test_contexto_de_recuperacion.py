"""`control.contexto_de_recuperacion` y sus parámetros opcionales (SL-E6, RP7-5, RP7-10).

La bitácora de la 0.7.0 (S2-3, «Sin prueba propia») anota que la función solo se ejercía de forma
indirecta por `test_decision_crea_version.py`. Aquí se prueba directa sobre OB-S2 con V-01 y V-02 y
los precios del corte; cada cifra esperada sale de la memoria a mano
`tests/fixtures/memorias/control_ob_s2.md` (§1, §4 y §8) o de aritmética exacta aparte, nunca de la
función bajo prueba:

* sin opcionales: venta 5 060,00, costo fijo 600,00, sin reajuste; «más cuadrillas» día 17 y
  ΔCD 120,00; «horas extra» día 21; «aceptar» día 23 con costo indirecto 90,00;
* `objetivo`: frontera 22 / 23 sobre los fines reproyectados (C termina en 22,5);
* `horas_previas`: frontera 78 / 78,01 contra el tope anual de 100 h (art. 178, a cotejar): el
  obrero de C suma 2 h × 11 días = 22 h;
* `origen_costo_diario`: viaja como supuesto declarado de cada opción que aplica;
* `independientes`: no cambia ninguna opción (RP7-10: el paralelo se calcula siempre y la
  declaración se exige al elegir).

Datos ficticios (NORMAS.md §1).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.budget.control import (
    calcular_control,
    composiciones_de_la_linea_base,
    contexto_de_recuperacion,
)
from core.budget.recuperacion import opciones
from core.catalog import Catalogo
from tests.fixtures import control_ob_s2 as ob

D = Decimal
TOLERANCIA = D("0.000001")


@pytest.fixture
def al_corte(obra):
    """El control de OB-S2 al corte 2026-11-13 y las composiciones de su línea base."""
    ob.registrar_v01_y_v02(obra)
    resultado = calcular_control(
        obra, ob.NOMBRE, catalogo=Catalogo(obra), precios=ob.precios_del_corte()
    )
    return resultado, composiciones_de_la_linea_base(resultado)


def _por_nombre(contexto):
    return {o.nombre: o for o in opciones(contexto)}


def test_sin_opcionales_el_contexto_lleva_el_corte_y_los_montos_de_la_memoria(al_corte):
    resultado, composiciones = al_corte
    contexto = contexto_de_recuperacion(resultado, composiciones)
    # Lo que se pasa tal cual (identidad, no igualdad: no se recalcula nada).
    assert contexto.estado is resultado.estado
    assert contexto.base is resultado.reproyeccion
    assert contexto.indicadores is resultado.indicadores
    assert contexto.composiciones is composiciones
    assert contexto.parametros is resultado.parametros
    assert contexto.parametros_costo == ob.PARAMETROS
    # Memoria §1: V = 5 060,00; CF = 600,00. Sin estudio de reajuste guardado: 0.
    assert contexto.venta == D("5060.00")
    assert contexto.costo_fijo == D("600.00")
    assert contexto.reajuste == D(0)
    # Valores por defecto declarados en la firma.
    assert contexto.objetivo is None and contexto.meta == 20  # D = 20 días hábiles
    assert contexto.horas_previas == D(0)
    assert contexto.independientes == frozenset()
    assert contexto.origen_costo_diario == "composiciones de la linea base"


def test_sin_opcionales_las_opciones_son_las_de_la_memoria(al_corte):
    por_nombre = _por_nombre(contexto_de_recuperacion(*al_corte))
    cuadrillas = por_nombre["cuadrillas"]
    assert (cuadrillas.aplica, cuadrillas.termino, cuadrillas.retraso) == (True, 17, 0)
    assert abs(cuadrillas.costo_directo_adicional - D("120.00")) <= TOLERANCIA
    horas = por_nombre["horas_extra"]
    assert (horas.aplica, horas.termino, horas.retraso) == (True, 21, 1)
    assert abs(horas.costo_directo_adicional - D("115.3125")) <= TOLERANCIA
    aceptar = por_nombre["aceptar"]
    assert (aceptar.termino, aceptar.retraso) == (23, 3)
    assert aceptar.costo_indirecto == D(600) * 23 / 20 - D(600) == D(90)
    assert por_nombre["paralelo"].aplica is False


def test_un_objetivo_de_22_deja_a_c_como_unica_partida_determinante(al_corte):
    """C termina en 22,5 y B en 21,67 (memoria §4): con objetivo 22 solo C pasa del objetivo. Con
    k = 2 (E = 1,8) C termina en 16,94; ΔCD = 100 × 80 × (2 − 1,8) / (10 × 1,8) = 1 600 / 18."""
    contexto = contexto_de_recuperacion(*al_corte, objetivo=22)
    assert contexto.meta == 22
    cuadrillas = _por_nombre(contexto)["cuadrillas"]
    assert cuadrillas.aplica is True
    assert set(cuadrillas.detalle["partidas"]) == {"OB-C"}
    assert cuadrillas.detalle["partidas"]["OB-C"]["k"] == 2
    assert abs(cuadrillas.costo_directo_adicional - D(1600) / D(18)) <= TOLERANCIA
    assert (cuadrillas.termino, cuadrillas.retraso) == (22, 0)  # B sigue en 21,67 → día 22


def test_un_objetivo_de_23_ya_no_tiene_partidas_que_lo_pasen(al_corte):
    contexto = contexto_de_recuperacion(*al_corte, objetivo=23)
    por_nombre = _por_nombre(contexto)
    for nombre in ("cuadrillas", "horas_extra"):
        assert (por_nombre[nombre].aplica, por_nombre[nombre].motivo) == (
            False,
            "ninguna partida pasa del objetivo",
        ), nombre
    aceptar = por_nombre["aceptar"]
    assert (aceptar.termino, aceptar.retraso, aceptar.penalizacion) == (23, 0, D(0))


def test_las_horas_previas_en_el_tope_anual_pasan_y_un_centesimo_mas_no(al_corte):
    """Peor obrero: C con fin 20,42 → día 21, 11 días hábiles tras el corte (día 10) a 2 h:
    22 h. 78 + 22 = 100 (el límite exacto pasa); 78,01 + 22 = 100,01 no."""
    en_el_tope = _por_nombre(contexto_de_recuperacion(*al_corte, horas_previas=D(78)))
    assert en_el_tope["horas_extra"].aplica is True
    assert en_el_tope["horas_extra"].termino == 21
    pasado = _por_nombre(contexto_de_recuperacion(*al_corte, horas_previas=D("78.01")))
    assert pasado["horas_extra"].aplica is False
    assert "100.01 h extra" in pasado["horas_extra"].motivo
    assert "art. 178" in pasado["horas_extra"].motivo
    # Las horas previas no tocan las otras opciones.
    assert pasado["cuadrillas"] == en_el_tope["cuadrillas"]


def test_el_origen_del_costo_diario_queda_como_supuesto_declarado(al_corte):
    origen = "APU revalorados al corte (ficticio)"
    contexto = contexto_de_recuperacion(*al_corte, origen_costo_diario=origen)
    assert contexto.origen_costo_diario == origen
    for nombre, opcion in _por_nombre(contexto).items():
        if not opcion.aplica:
            continue
        declarados = {
            (s.nombre, s.valor, s.naturaleza)
            for s in opcion.supuestos
            if s.nombre == "costo diario de la cuadrilla"
        }
        assert declarados == {("costo diario de la cuadrilla", origen, "SUPUESTO_DECLARADO")}, (
            nombre
        )


def test_declarar_independientes_no_cambia_ninguna_opcion(al_corte):
    """RP7-10: el paralelo se calcula siempre y se presenta; la declaración se exige al elegirlo
    (`aplicar_decision`), no al calcular."""
    sin = opciones(contexto_de_recuperacion(*al_corte))
    con = contexto_de_recuperacion(*al_corte, independientes=frozenset({"OB-C"}))
    assert con.independientes == frozenset({"OB-C"})
    assert opciones(con) == sin
