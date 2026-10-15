"""SL-E9: diferencia entre versiones y revaloración, contra la memoria hecha a mano
(`tests/fixtures/memorias/diferencias_s3.md`; RF-87, RV-10; spec S3 §9 paso 4 y §13.1).

Las cifras esperadas son las de la memoria (aritmética exacta a mano), nunca las de la función bajo
prueba. Todo es `Decimal`: las igualdades son exactas por diseño (sin redondeos en el módulo)."""

from __future__ import annotations

import copy
from decimal import Decimal, getcontext, localcontext
from fractions import Fraction

import pytest

from core.budget import canonico
from core.budget.comparacion import (
    FilaPresupuesto,
    PrecioDeLista,
    diferencia_entre_versiones,
    filas_de,
    revalorar,
)
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1


def fila(codigo: str, q: str, pu: str) -> FilaPresupuesto:
    return FilaPresupuesto(codigo, f"partida {codigo}", "m", Decimal(q), Decimal(pu))


#: Versión 004 y versión 005 de la memoria §1: A cambia solo la cantidad, B solo el precio, C las
#: dos cosas, D se elimina y E es nueva.
V004 = (
    fila("A", "10", "50.00"),
    fila("B", "5", "20.00"),
    fila("C", "2", "100.00"),
    fila("D", "4", "10.00"),
)
V005 = (
    fila("A", "12", "50.00"),
    fila("B", "5", "22.00"),
    fila("C", "3", "110.00"),
    fila("E", "3", "30.00"),
)
#: código: (estado, Δ por cantidad, Δ por precio), hechos a mano en la memoria §1.
MEMORIA = {
    "A": ("cambiada", "100.00", "0.00"),
    "B": ("cambiada", "0.00", "10.00"),
    "C": ("cambiada", "100.00", "30.00"),
    "D": ("eliminada", "-40.00", "0.00"),
    "E": ("nueva", "90.00", "0.00"),
}

#: La entrega paralela Q de la memoria §1b (protocolo del indicador de quien revisa).
Q_V1 = (fila("A'", "8", "25"), fila("B'", "6", "15"), fila("C'", "4", "40"), fila("D'", "2", "50"))
Q_V2 = (fila("A'", "9", "25"), fila("B'", "6", "16"), fila("C'", "5", "44"), fila("E'", "4", "12"))
MEMORIA_Q = {
    "A'": ("cambiada", "25", "0"),
    "B'": ("cambiada", "0", "6"),
    "C'": ("cambiada", "40", "20"),
    "D'": ("eliminada", "-100", "0"),
    "E'": ("nueva", "48", "0"),
}


def test_la_diferencia_por_partida_es_la_de_la_memoria() -> None:
    diferencia = diferencia_entre_versiones(V004, V005)
    por_codigo = {p.codigo_partida: p for p in diferencia.partidas}
    assert set(por_codigo) == set(MEMORIA)
    for codigo, (estado, dq, dp) in MEMORIA.items():
        parcial = por_codigo[codigo]
        assert (parcial.estado, parcial.desvio_cantidad, parcial.desvio_precio) == (
            estado,
            Decimal(dq),
            Decimal(dp),
        ), codigo
        assert parcial.desvio_total == Decimal(dq) + Decimal(dp)


def test_los_totales_son_los_de_la_memoria_y_las_dos_columnas_suman_exacto() -> None:
    diferencia = diferencia_entre_versiones(V004, V005)
    assert (diferencia.total_1, diferencia.total_2) == (Decimal("840.00"), Decimal("1130.00"))
    assert (diferencia.desvio_cantidad, diferencia.desvio_precio) == (
        Decimal("250.00"),
        Decimal("40.00"),
    )
    assert diferencia.desvio_total == Decimal("290.00")
    assert diferencia.desvio_cantidad + diferencia.desvio_precio == (
        diferencia.total_2 - diferencia.total_1
    )


def test_la_entrega_q_de_la_memoria_va_de_550_a_589() -> None:
    """§1b: 550 → 589; Σ Δ cantidad 13, Σ Δ precio 26, orden D', C', E', A', B'."""
    diferencia = diferencia_entre_versiones(Q_V1, Q_V2)
    assert (diferencia.total_1, diferencia.total_2) == (Decimal(550), Decimal(589))
    assert (diferencia.desvio_cantidad, diferencia.desvio_precio) == (Decimal(13), Decimal(26))
    assert diferencia.desvio_total == Decimal(39)
    por_codigo = {p.codigo_partida: p for p in diferencia.partidas}
    for codigo, (estado, dq, dp) in MEMORIA_Q.items():
        parcial = por_codigo[codigo]
        assert (parcial.estado, parcial.desvio_cantidad, parcial.desvio_precio) == (
            estado,
            Decimal(dq),
            Decimal(dp),
        ), codigo
    assert [p.codigo_partida for p in diferencia.partidas] == ["D'", "C'", "E'", "A'", "B'"]


def test_se_ordena_por_el_valor_absoluto_del_delta() -> None:
    codigos = [p.codigo_partida for p in diferencia_entre_versiones(V004, V005).partidas]
    assert codigos == ["C", "A", "E", "D", "B"]  # 130, 100, 90, 40, 10


def test_a_igual_delta_absoluto_desempata_el_codigo() -> None:
    """Frontera del orden: +10 y -10 empatan en |Δ| y salen por código."""
    a = (fila("Z", "1", "10"), fila("M", "2", "10"))
    b = (fila("Z", "2", "10"), fila("M", "1", "10"))
    assert [p.codigo_partida for p in diferencia_entre_versiones(a, b).partidas] == ["M", "Z"]


def test_el_termino_cruzado_queda_en_el_precio() -> None:
    """C: (3 - 2) x 100 = 100 por cantidad; (110 - 100) x 3 = 30 por precio (no 20)."""
    c = {p.codigo_partida: p for p in diferencia_entre_versiones(V004, V005).partidas}["C"]
    assert (c.desvio_cantidad, c.desvio_precio) == (Decimal("100.00"), Decimal("30.00"))


def test_una_partida_nueva_o_eliminada_es_desvio_por_cantidad_entero() -> None:
    nueva = diferencia_entre_versiones((), (fila("N", "3", "30.00"),)).partidas[0]
    assert (nueva.estado, nueva.cantidad_1, nueva.precio_1) == ("nueva", 0, Decimal("30.00"))
    assert (nueva.desvio_cantidad, nueva.desvio_precio) == (Decimal("90.00"), 0)
    borrada = diferencia_entre_versiones((fila("X", "4", "10.00"),), ()).partidas[0]
    assert (borrada.estado, borrada.cantidad_2, borrada.precio_2) == ("eliminada", 0, Decimal(10))
    assert (borrada.desvio_cantidad, borrada.desvio_precio) == (Decimal("-40.00"), 0)


def test_dos_versiones_iguales_no_difieren() -> None:
    diferencia = diferencia_entre_versiones(V004, V004)
    assert diferencia.desvio_total == 0 and {p.estado for p in diferencia.partidas} == {"igual"}


def test_dos_versiones_vacias_dan_una_diferencia_vacia() -> None:
    diferencia = diferencia_entre_versiones((), ())
    assert diferencia.partidas == ()
    assert (diferencia.total_1, diferencia.total_2, diferencia.desvio_total) == (0, 0, 0)


def test_las_filas_repetidas_de_una_partida_suman_cantidad_con_un_solo_precio() -> None:
    junto = diferencia_entre_versiones(
        (fila("A", "1", "5"), fila("A", "2", "5")), (fila("A", "6", "5"),)
    )
    assert junto.partidas[0].cantidad_1 == Decimal(3) and junto.desvio_total == Decimal(15)
    with pytest.raises(ValueError, match="dos precios unitarios"):
        diferencia_entre_versiones((fila("A", "1", "5"), fila("A", "2", "6")), ())


def test_el_ejemplo_del_spec_no_pierde_centimos() -> None:
    """Rehecho con fracciones (aritmética exacta aparte, no `Decimal`)."""
    a = (fila("P", "7", "33.333333"),)
    b = (fila("P", "9", "35.100001"),)
    d = diferencia_entre_versiones(a, b)
    esperado = 9 * Fraction("35.100001") - 7 * Fraction("33.333333")
    assert Fraction(d.desvio_cantidad + d.desvio_precio) == esperado
    assert Fraction(d.desvio_cantidad) == (9 - 7) * Fraction("33.333333")
    assert Fraction(d.desvio_precio) == (Fraction("35.100001") - Fraction("33.333333")) * 9


def test_el_contexto_decimal_del_hilo_no_cambia_el_resultado() -> None:
    """Con una precisión de 3 dígitos en el hilo, la diferencia sigue exacta (prec 28 propia)."""
    with localcontext() as ctx:
        ctx.prec = 3
        d = diferencia_entre_versiones((fila("P", "7", "33.333333"),), (fila("P", "9", "35.1"),))
        assert getcontext().prec == 3
    esperado = 9 * Fraction("35.1") - 7 * Fraction("33.333333")
    assert Fraction(d.desvio_total) == esperado


# --- revaloración -------------------------------------------------------------------------


def documento(**cambios) -> canonico.DocumentoLeido:
    objeto = copy.deepcopy(EJEMPLO_V1)
    if cambios.get("referencia"):
        objeto["composiciones"][0]["lineas"][0]["referencia"] = cambios["referencia"]
    return canonico.leer(objeto)


def test_filas_de_recalcula_el_precio_en_vez_de_creer_el_declarado() -> None:
    objeto = copy.deepcopy(EJEMPLO_V1)
    objeto["renglones"][0]["precio_unitario"] = "99.00"  # el emisor miente
    leido = canonico.leer(objeto)
    assert filas_de(leido)[0].precio_unitario == Decimal("41.83987500")
    assert leido.declarados[0].precio_unitario == Decimal("99.00")


def test_revalorar_empareja_por_codigo_y_lo_que_no_empareja_no_suma() -> None:
    lista = [
        PrecioDeLista("MAT-001", "", Decimal("16.00")),
        PrecioDeLista("MO-001", "", Decimal("12.25")),
    ]  # la compactadora no está
    revalorado = revalorar(documento(), lista)
    assert revalorado.filas[0].precio_unitario == Decimal("48.797375")  # memoria §2, a mano
    assert [(n.insumo, n.descripcion) for n in revalorado.no_contrastables] == [
        ("EQU-001", "Compactadora")
    ]
    diferencia = diferencia_entre_versiones(filas_de(documento()), revalorado.filas)
    assert diferencia.desvio_precio == Decimal("139.15")  # (48.797375 - 41.839875) x 20
    assert diferencia.desvio_cantidad == 0


def test_la_referencia_de_precio_manda_sobre_el_codigo() -> None:
    lista = [
        PrecioDeLista("OTRO-9", "MP-0042", Decimal("15.00")),
        PrecioDeLista("MAT-001", "", Decimal("16.00")),
        PrecioDeLista("MO-001", "", Decimal("12.25")),
        PrecioDeLista("EQU-001", "", Decimal("71.00")),
    ]
    revalorado = revalorar(documento(referencia="MP-0042"), lista)
    diferencia = diferencia_entre_versiones(filas_de(documento()), revalorado.filas)
    assert revalorado.no_contrastables == ()
    assert revalorado.filas[0].precio_unitario == Decimal("47.532375")  # Arena 15,00; Obrero 12,25
    assert diferencia.desvio_precio == Decimal("113.85")  # (47.532375 - 41.839875) x 20


def test_una_lista_vacia_deja_todo_no_contrastable_y_el_delta_en_cero() -> None:
    revalorado = revalorar(documento(), [])
    assert {n.insumo for n in revalorado.no_contrastables} == {"EQU-001", "MAT-001", "MO-001"}
    assert len(revalorado.no_contrastables) == 3
    assert diferencia_entre_versiones(filas_de(documento()), revalorado.filas).desvio_total == 0
