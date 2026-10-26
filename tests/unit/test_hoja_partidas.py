"""Partidas a mano en el borrador de la Hoja (plan MP, Tarea 8).

La persona agrega una partida del catálogo con su cantidad y, si quiere, «cómo se midió» (el
cálculo, con coma decimal) y una nota; también puede quitar un renglón que no salga del espacio.
Todo vive en el borrador (inmutable) y se ve en sus cambios como alta o baja.

Oráculos a mano (ninguno sale del código bajo prueba):

- «6*3-2» = 18 − 2 = 16; «10/3» = 3,33333… → 3,3333 a cuatro decimales; «6*35» = 210.
- «0,00005*1» = 0,00005 → a cuatro decimales con redondeo «la mitad hacia arriba» 0,0001 (con
  el redondeo bancario daría 0,0000).
- «50*2» = 100 y «2,50*2» = 5,00: se escriben «100» y «5» (sin exponente ni ceros a la derecha).
- Tolerancia de la cantidad escrita frente al cálculo: la diferencia no pasa de 0,001 y, como la
  regla R1 la compara en forma relativa (0,001 × el resultado), tampoco de esa fracción.
  16,0005 frente a 16: 0,0005 ≤ 0,001 y ≤ 0,016 → vale. 16,002 frente a 16: 0,002 > 0,001 →
  no. 0,5008 frente a «1/2» = 0,5: 0,0008 ≤ 0,001 pero > 0,0005 (0,001 × 0,5) → no, porque R1
  la marcaría como error.
- La advertencia de R1 para una cantidad manual sin regla la escribe el núcleo
  (`core/verification/reglas.py`, «la cantidad de X (Q U) es manual y no declara la regla…»);
  su versión llana es el texto de la Tarea 8, copiado del plan.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from decimal import Decimal

import pytest

from aplicacion import hoja
from aplicacion.cifras import MENSAJE_CIFRA, CifraInvalida
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_partidas import (
    CalculoInvalido,
    PartidaElegida,
    agregar_partida,
    cantidad_y_regla,
    quitar_partida,
    texto_llano,
    traducir_calculo,
)
from core.budget import CambioEditado
from core.contracts import ItemComputo, OrigenTipo, Severidad
from core.contracts.dominio import Dominio
from tests.fixtures.hoja_borrador import FECHA, borrador_bano, composiciones_sinteticas

D = Decimal

#: El texto del plan (Tarea 8) para un carácter que no es cifra, signo, paréntesis ni espacio.
SOLO_ARITMETICA = "El cálculo solo admite números y los signos + − × / y paréntesis."
#: La versión llana de la advertencia de R1, copiada del plan con OBRA-04 y 210 m2.
LLANO_OBRA_04 = (
    "La cantidad de OBRA-04 (210 m2) se escribió a mano sin cálculo: escriba cómo se obtuvo si "
    "quiere que Sílice la pueda verificar."
)

MURO = PartidaElegida(
    codigo="OBRA-04",
    descripcion="Paredes de bloque de arcilla",
    unidad="m2",
    dominio=Dominio.CIVIL,
)
CLAVE_1 = "OBRA-04|a-mano:1"
CLAVE_2 = "OBRA-04|a-mano:2"


def _vacio() -> hoja.Borrador:
    """Un borrador en blanco (sin espacio ni renglones) con el APU sintético de OBRA-04."""
    item = ItemComputo(
        MURO.codigo, MURO.descripcion, MURO.unidad, D("1"), "x", OrigenTipo.MANUAL, MURO.dominio
    )
    return hoja.Borrador(fecha=FECHA, composiciones=composiciones_sinteticas([item]))


def _agregar(borrador: hoja.Borrador, cantidad: str = "210", calculo: str = "", nota: str = ""):
    return agregar_partida(borrador, MURO, cantidad=cantidad, calculo=calculo, nota=nota)


# --- traducir_calculo -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("escrito", "traducido"),
    [
        ("2,5*4", "2.5*4"),
        ("6*3-2", "6*3-2"),
        ("1.234,5*2", "1234.5*2"),
        ("6 × 3", "6*3"),
        ("6 x 3", "6*3"),
        ("(2,5 + 1) / 2", "(2.5+1)/2"),
        ("6 − 1", "6-1"),  # el signo menos tipográfico del propio mensaje de error
        ("  6*35  ", "6*35"),
    ],
)
def test_traducir_calculo_reescribe_las_cifras_con_punto_decimal_y_sin_miles(escrito, traducido):
    assert traducir_calculo(escrito) == traducido


@pytest.mark.parametrize("escrito", ["2.5*4", "1 234*2", "1,2,3*2", "2,*4", "1.2345*2"])
def test_una_cifra_mal_escrita_en_el_calculo_dice_la_regla_de_las_cifras(escrito):
    with pytest.raises(CalculoInvalido) as error:
        traducir_calculo(escrito)
    assert str(error.value) == MENSAJE_CIFRA


@pytest.mark.parametrize(
    "escrito",
    [
        "6*a",
        "2**10",
        "9**9**9",
        "__import__('os').system('echo hola')",
        "open('x').read()",
        "().__class__",
        "1e3*2",
        "1_000*2",
        "2;3",
        "6=6",
        "6%4",
        "6//4",
    ],
)
def test_otro_caracter_o_construccion_se_rechaza_sin_ejecutar_nada(escrito):
    with pytest.raises(CalculoInvalido) as error:
        traducir_calculo(escrito)
    assert str(error.value) == SOLO_ARITMETICA


def test_un_texto_malicioso_no_llega_a_ejecutarse(monkeypatch):
    """Ni `eval` ni `exec` intervienen: si alguien los llamara, la prueba fallaría."""

    def prohibido(*_args, **_kwargs):
        raise AssertionError("el cálculo no se evalúa con eval/exec de Python")

    monkeypatch.setattr("builtins.eval", prohibido)
    monkeypatch.setattr("builtins.exec", prohibido)
    assert cantidad_y_regla("", "(6+4)*2,5") == (D("25"), "(6+4)*2.5")
    with pytest.raises(CalculoInvalido):
        cantidad_y_regla("", "__import__('os').system('echo hola')")


def test_un_calculo_muy_largo_o_muy_anidado_se_rechaza_sin_desbordar():
    profundo = "(" * 400 + "1" + ")" * 400
    largo = "+".join(["1"] * (sys.getrecursionlimit() + 10))
    for texto in (profundo, largo):
        with pytest.raises(CalculoInvalido):
            cantidad_y_regla("", texto)


# --- cantidad_y_regla -------------------------------------------------------------------------


def test_sin_cantidad_la_cantidad_es_el_resultado_del_calculo():
    assert cantidad_y_regla("", "6*3-2") == (D("16"), "6*3-2")


def test_el_resultado_se_redondea_a_cuatro_decimales_la_mitad_hacia_arriba():
    assert cantidad_y_regla("", "10/3") == (D("3.3333"), "10/3")
    assert cantidad_y_regla("", "0,00005*1") == (D("0.0001"), "0.00005*1")


def test_el_resultado_no_lleva_exponente_ni_ceros_a_la_derecha():
    cien, _ = cantidad_y_regla("", "50*2")
    cinco, _ = cantidad_y_regla("", "2,50*2")
    assert (str(cien), str(cinco)) == ("100", "5")


def test_cantidad_y_calculo_que_no_coinciden_se_rechazan_con_las_dos_cifras():
    with pytest.raises(CalculoInvalido) as error:
        cantidad_y_regla("15", "6*3-2")
    assert str(error.value) == "El cálculo da 16 y la cantidad es 15: corrija uno de los dos."


def test_cantidad_dentro_de_la_tolerancia_se_queda_como_se_escribio():
    assert cantidad_y_regla("16,0005", "6*3-2") == (D("16.0005"), "6*3-2")
    assert cantidad_y_regla("1.234,5", "1.234,5*1") == (D("1234.5"), "1234.5*1")


def test_fuera_de_la_tolerancia_absoluta_se_rechaza():
    with pytest.raises(CalculoInvalido) as error:
        cantidad_y_regla("16,002", "6*3-2")
    assert str(error.value) == "El cálculo da 16 y la cantidad es 16,002: corrija uno de los dos."


def test_fuera_de_la_tolerancia_relativa_de_r1_se_rechaza_aunque_la_absoluta_pase():
    with pytest.raises(CalculoInvalido) as error:
        cantidad_y_regla("0,5008", "1/2")
    assert str(error.value) == "El cálculo da 0,5 y la cantidad es 0,5008: corrija uno de los dos."


def test_el_mensaje_dice_el_resultado_a_cuatro_decimales():
    with pytest.raises(CalculoInvalido) as error:
        cantidad_y_regla("3", "10/3")
    assert str(error.value) == "El cálculo da 3,3333 y la cantidad es 3: corrija uno de los dos."


def test_sin_calculo_la_cantidad_es_la_escrita_y_no_hay_regla():
    assert cantidad_y_regla("210", "") == (D("210"), None)
    assert cantidad_y_regla("1.234,5", "   ") == (D("1234.5"), None)


def test_una_cantidad_mal_escrita_dice_la_regla_de_las_cifras():
    with pytest.raises(CifraInvalida) as error:
        cantidad_y_regla("2.5", "")
    assert str(error.value) == MENSAJE_CIFRA


@pytest.mark.parametrize(
    ("cantidad", "calculo", "mensaje"),
    [
        ("", "1/0", "El cálculo no se puede hacer: revise los signos y los paréntesis."),
        ("", "6*", "El cálculo no se puede hacer: revise los signos y los paréntesis."),
        ("", "(6*3", "El cálculo no se puede hacer: revise los signos y los paréntesis."),
        ("", "2-5", "El cálculo da -3: una cantidad no puede ser negativa."),
        ("-5", "", "La cantidad no puede ser negativa."),
    ],
)
def test_calculos_imposibles_y_cantidades_negativas_se_rechazan(cantidad, calculo, mensaje):
    with pytest.raises(CalculoInvalido) as error:
        cantidad_y_regla(cantidad, calculo)
    assert str(error.value) == mensaje


# --- agregar_partida --------------------------------------------------------------------------


def test_agregar_a_un_borrador_vacio_es_un_alta_con_su_clave_y_su_nota():
    base = _vacio()
    nuevo, clave = _agregar(base, "210", "", "6 m × 35 m de muro")
    assert clave == CLAVE_1
    assert nuevo.items_base == (
        ItemComputo(
            "OBRA-04",
            "Paredes de bloque de arcilla",
            "m2",
            D("210"),
            "a-mano:1",
            OrigenTipo.MANUAL,
            Dominio.CIVIL,
            regla=None,
        ),
    )
    assert nuevo.items_base[0].parametros == {}
    assert nuevo.notas == {CLAVE_1: "6 m × 35 m de muro"}
    assert hoja.cambios_entre(base, nuevo) == [
        CambioEditado("cantidad", CLAVE_1, "alta", "", "210")
    ]
    assert base.items_base == () and base.notas == {}  # el borrador es inmutable


def test_agregar_con_calculo_guarda_el_calculo_traducido_como_regla():
    nuevo, clave = _agregar(_vacio(), "", "6*35", "")
    (item,) = nuevo.items_base
    assert (clave, item.cantidad, item.regla) == (CLAVE_1, D("210"), "6*35")
    assert nuevo.notas == {}  # una nota vacía no se guarda


def test_agregar_dos_veces_da_claves_distintas():
    base = _vacio()
    uno, primera = _agregar(base)
    dos, segunda = _agregar(uno, "35")
    assert (primera, segunda) == (CLAVE_1, CLAVE_2)
    assert hoja.cambios_entre(base, dos) == [
        CambioEditado("cantidad", CLAVE_1, "alta", "", "210"),
        CambioEditado("cantidad", CLAVE_2, "alta", "", "35"),
    ]


def test_el_numero_sigue_al_mayor_de_los_agregados():
    uno, _ = _agregar(_vacio())
    dos, _ = _agregar(uno)
    sin_primera = quitar_partida(dos, CLAVE_1)
    _, clave = _agregar(sin_primera)
    assert clave == "OBRA-04|a-mano:3"


def test_agregar_no_cambia_lo_que_sale_del_espacio():
    base = borrador_bano()
    nuevo, clave = _agregar(base, "12,5")
    assert hoja.cambios_entre(base, nuevo) == [CambioEditado("cantidad", clave, "alta", "", "12.5")]
    assert nuevo.espacio == base.espacio


def test_el_alta_lleva_la_cantidad_escrita_y_nunca_a_la_vez_un_cambio_de_cantidad():
    base = _vacio()
    nuevo, clave = _agregar(base)
    escrito = replace(nuevo, cantidades={clave: D("215")})
    assert hoja.cambios_entre(base, escrito) == [
        CambioEditado("cantidad", CLAVE_1, "alta", "", "215")
    ]


def test_cambiar_la_cantidad_de_un_renglon_ya_guardado_sigue_siendo_un_cambio_de_cantidad():
    guardado, clave = _agregar(_vacio())
    escrito = replace(guardado, cantidades={clave: D("215")})
    assert hoja.cambios_entre(guardado, escrito) == [
        CambioEditado("cantidad", CLAVE_1, "cantidad", "210", "215")
    ]


# --- quitar_partida ---------------------------------------------------------------------------


def test_quitar_la_primera_es_una_baja_con_su_cantidad():
    dos, _ = _agregar(_agregar(_vacio(), nota="muro norte")[0], "35", nota="muro sur")
    sin_primera = quitar_partida(dos, CLAVE_1)
    assert [i.origen_id for i in sin_primera.items_base] == ["a-mano:2"]
    assert sin_primera.notas == {CLAVE_2: "muro sur"}
    assert hoja.cambios_entre(dos, sin_primera) == [
        CambioEditado("cantidad", CLAVE_1, "baja", "210", "")
    ]


def test_quitar_tambien_quita_la_cantidad_escrita_y_la_baja_la_dice():
    agregado, clave = _agregar(_vacio())
    escrito = replace(agregado, cantidades={clave: D("300")})
    sin_ella = quitar_partida(escrito, clave)
    assert (sin_ella.items_base, dict(sin_ella.cantidades)) == ((), {})
    assert hoja.cambios_entre(escrito, sin_ella) == [
        CambioEditado("cantidad", clave, "baja", "300", "")
    ]


def test_agregar_y_quitar_antes_de_guardar_no_deja_cambios():
    base = _vacio()
    agregado, clave = _agregar(base, nota="se quita")
    assert hoja.cambios_entre(base, quitar_partida(agregado, clave)) == []


def test_una_fila_del_espacio_no_se_quita_desde_el_presupuesto():
    base = borrador_bano()
    del_espacio = hoja.claves_de_items(hoja.items_sin_escribir(base))[0]
    with pytest.raises(HojaInvalida) as error:
        quitar_partida(base, del_espacio)
    assert str(error.value) == "Esa fila sale del espacio: cámbiela en «Espacio y metrajes»."


def test_una_clave_que_no_esta_en_el_borrador_no_se_quita():
    with pytest.raises(HojaInvalida) as error:
        quitar_partida(_vacio(), CLAVE_1)
    assert str(error.value) == "Esa fila ya no está en el presupuesto."


# --- la regla R1 y su texto llano ---------------------------------------------------------------


def _hallazgos_r1(borrador: hoja.Borrador, origen: str):
    informe = hoja.elaborar_borrador(borrador).elaboracion.informe
    return [h for h in informe.hallazgos if h.regla == "R1" and origen in h.origen_ids]


def test_con_calculo_r1_no_dice_nada_de_la_partida_agregada():
    nuevo, _ = _agregar(_vacio(), "", "6*35")
    assert _hallazgos_r1(nuevo, "a-mano:1") == []


def test_sin_calculo_r1_advierte_y_su_texto_llano_es_el_del_plan():
    nuevo, _ = _agregar(_vacio(), "210", "")
    (advertencia,) = _hallazgos_r1(nuevo, "a-mano:1")
    assert advertencia.severidad is Severidad.ADVERTENCIA
    assert texto_llano(advertencia.descripcion) == LLANO_OBRA_04


def test_texto_llano_deja_igual_cualquier_otra_descripcion():
    otra = "la cantidad de OBRA-04 es 15 m2, pero su regla '6*3-2' evaluada da 16 m2"
    assert texto_llano(otra) == otra
