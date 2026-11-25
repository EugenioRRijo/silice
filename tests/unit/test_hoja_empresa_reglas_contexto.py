"""Pruebas directas de `_Analizador`, `_Contexto`, `_iguales` y utilidades de formato.

Cubren fronteras y ramas de `adapters/hoja_empresa/reglas_contexto.py` señaladas por mutación
con libros sintéticos de `tests/fixtures/libros_empresa.py` y fórmulas en texto.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from functools import lru_cache

from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import Celda
from adapters.hoja_empresa.perfil import cargar_perfil
from adapters.hoja_empresa.reglas_contexto import (
    _Analizador,
    _Contexto,
    _fu,
    _iguales,
    _Lectura,
    _valor,
)
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    D,
    PartidaSinApu,
    Siembra,
    construir_libro,
    libro_limpio,
)


@lru_cache(maxsize=1)
def _libro_base():
    return leer_libro(libro_limpio().datos, "limpio.xlsx")


def test_fu_y_valor_formato_y_umbrales():
    """Mata mutantes en formato y límites: 116 or->and, 120 or->and, 125 > -> >=."""
    assert _fu(Decimal("1.5")) == "1,5"
    assert _fu(Decimal("0")) == "0"
    assert _valor(None) == "vacía"
    assert _valor("") == "vacía"
    assert _valor("a" * 60) == f"«{'a' * 60}»"
    assert _valor("a" * 61) == f"«{'a' * 60}…»"


def test_lectura_pura_n_iferror_if_e_indirect():
    """Mata mutantes en `_cierre`, `_argumentos` y `lectura_pura`:
    165 < -> <=, 168 delete not, 188 delete not, 193 1->0, 338 == -> != / 1->0, 339 0->1,
    340 True->False, 342 == -> != / and->or, 343 0->1, 345 == -> != / and->or / 1->0,
    348 and->or, 352 True->False.
    """
    an = _Analizador(_libro_base())
    b5 = _Lectura(Celda("PRESUPUESTO", "B5"))
    c5 = _Lectura(Celda("PRESUPUESTO", "C5"))

    assert an.lectura_pura("=N(B5)", "PRESUPUESTO") == _Lectura(
        Celda("PRESUPUESTO", "B5"), numerica=True
    )
    assert an.lectura_pura("=ABS(B5)", "PRESUPUESTO") is None
    assert an.lectura_pura("=N(B5", "PRESUPUESTO") is None

    assert an.lectura_pura("=IFERROR(B5, 0)", "PRESUPUESTO") == b5
    assert an.lectura_pura("=IFERROR(N(B5), 0)", "PRESUPUESTO") == _Lectura(
        Celda("PRESUPUESTO", "B5"), numerica=True
    )
    assert an.lectura_pura("=SUM(B5, C5)", "PRESUPUESTO") is None

    assert an.lectura_pura('=IF(B5="", "", C5)', "PRESUPUESTO") == c5
    assert an.lectura_pura('=IF(B5=")", "", C5)', "PRESUPUESTO") == c5
    assert an.lectura_pura('=IF(B5="x,y", "", C5)', "PRESUPUESTO") == c5
    assert an.lectura_pura("=IF(B5=0, 0, C5)", "PRESUPUESTO") is None
    assert an.lectura_pura("=FOO(B5, C5, D5)", "PRESUPUESTO") is None

    assert an.lectura_pura("=INDIRECT(\"'APU-01'!G10\")", "PRESUPUESTO") == _Lectura(
        Celda("APU-01", "G10"), via_indirect=True
    )
    assert an.lectura_pura('=LEN("APU-01!G10")', "PRESUPUESTO") is None


def test_lectura_pura_uno_entre():
    """Mata mutantes en `_RX_UNO_ENTRE` de `lectura_pura`:
    355 + -> - (x3), 355 1->0 (x3), 355 0->1, 355 == -> !=, 356 1->0.
    """
    an = _Analizador(_libro_base())
    assert an.lectura_pura("=1/(1/B5)", "PRESUPUESTO") == _Lectura(Celda("PRESUPUESTO", "B5"))
    assert an.lectura_pura("=1/(1/B5)+1/(1/C5)", "PRESUPUESTO") is None


def test_nombre_a_celda_y_ref():
    """Mata mutantes en `nombre_a_celda`: 264 or->and, 264 1->0."""
    base = _libro_base()
    libro = replace(base, nombres={**base.nombres, "SIN_HOJA": "=$A$1"})
    an = _Analizador(libro)
    assert an.ref("PRECIOS", "APU-01") is None
    assert an.ref("SIN_HOJA", "APU-01") is None


def test_pieza_literales_text_y_referencias():
    """Mata mutantes en `_pieza`:
    280 >= -> >, 280 and->or, 280 1->0, 281 False->True, 285 and->or (x2),
    288 or->and, 290 True->False.
    """
    base = _libro_base()
    libro = replace(base, valores={**base.valores, "PRESUPUESTO!Z5": D("1.5")})
    an = _Analizador(libro)

    assert an._pieza('""', "PRESUPUESTO") == ("", False)
    assert an._pieza('"abc', "PRESUPUESTO") is None
    assert an._pieza("B5", "PRESUPUESTO") == ("1", True)
    assert an._pieza('TEXT($B5,"00")', "PRESUPUESTO") == ("01", True)
    assert an._pieza('OTRA($B5,"00")', "PRESUPUESTO") is None
    assert an._pieza('TEXT($B5,"##")', "PRESUPUESTO") is None
    assert an._pieza('TEXT(Z5,"00")', "PRESUPUESTO") is None


def test_indirect_fila_variable_y_ampersand_en_nombre():
    """Mata mutantes en `_partes_concat` e `indirect`:
    220 delete not, 306 False->True, 307 False->True, 313 and->or,
    314 True->False, 317 True->False, 325 True->False.
    """
    base = _libro_base()
    libro = replace(base, hojas=(*base.hojas, "A&B"))
    an = _Analizador(libro)

    assert an.indirect("\"'A&B'!G1\"", "PRESUPUESTO") == _Lectura(
        Celda("A&B", "G1"), via_indirect=True, fila_variable=False
    )
    assert an.indirect('"\'APU-"&TEXT($B5,"00")&"\'!G10"', "PRESUPUESTO") == _Lectura(
        Celda("APU-01", "G10"), via_indirect=True, fila_variable=False
    )
    assert an.indirect("\"'APU-01'!G\"&$B5", "PRESUPUESTO") == _Lectura(
        Celda("APU-01", "G1"), via_indirect=True, fila_variable=True
    )


def test_lecturas_indirect_al_inicio_sin_igual():
    """Mata mutantes en `lecturas`: 368 0->1, 372 < -> <=, 372 0->1."""
    an = _Analizador(_libro_base())
    assert an.lecturas("INDIRECT(\"'APU-01'!G10\")", "PRESUPUESTO") == [
        _Lectura(Celda("APU-01", "G10"), via_indirect=True)
    ]


def test_celdas_referidas_hoja_con_comillas_y_tope_de_rango():
    """Mata mutantes en `celdas_referidas`:
    395 1->0, 395 or->and, 401 - -> + (x2), 401 + -> - (x2), 401 1->0 (x2),
    401 * -> /, 401 > -> >=.
    """
    an = _Analizador(_libro_base())
    assert an.celdas_referidas("='APU-01'!G10", "PRESUPUESTO") == {"APU-01!G10"}
    assert an.celdas_referidas("=SUM(B2:B5)", "PRESUPUESTO", tope=4) == {
        "PRESUPUESTO!B2",
        "PRESUPUESTO!B3",
        "PRESUPUESTO!B4",
        "PRESUPUESTO!B5",
    }
    assert an.celdas_referidas("=SUM(B2:D4)", "PRESUPUESTO", tope=6) == set()


def test_contexto_indices_h_pres_y_etiqueta():
    """Mata mutantes en `_Contexto`: 424 and->or, 427 or->and, 466 and->or."""
    sin_apu = PartidaSinApu(4, "E.999.000.004", "Partida sin APU", "m2", D("1"), D("5"))
    c = construir_libro(APUS_LIMPIOS, Siembra(partidas_sin_apu=(sin_apu,)))
    libro_sin = leer_libro(c.datos, "sin_apu.xlsx")
    perfil = cargar_perfil(libro_sin.perfil)
    ctx_sin = _Contexto(libro_sin, perfil)
    assert None not in ctx_sin.partida_de_apu
    assert set(ctx_sin.partida_de_apu) == {"APU-01", "APU-02", "APU-03"}

    base = _libro_base()
    hojas_caja = tuple("Presupuesto" if h == "PRESUPUESTO" else h for h in base.hojas)
    ctx_caja = _Contexto(replace(base, hojas=hojas_caja), perfil)
    assert ctx_caja.h_pres == "Presupuesto"

    libro_esp = replace(base, valores={**base.valores, "RESUMEN!A2": "   ", "RESUMEN!B2": "Rótulo"})
    ctx_esp = _Contexto(libro_esp, perfil)
    assert ctx_esp.etiqueta("RESUMEN", 2) == "Rótulo"


def test_iguales_vacios_ceros_numeros_y_tipos_mixtos():
    """Mata mutantes en `_iguales`:
    526 or->and (x3), 526 == -> != (x3), 526 and->or,
    528 == -> !=, 528 and->or, 531 and->or, 533 and->or.
    """
    assert _iguales(None, Decimal(0)) is True
    assert _iguales(None, "") is True
    assert _iguales("", Decimal(0)) is True
    assert _iguales(None, Decimal(5)) is False
    assert _iguales(Decimal(5), Decimal(0)) is False
    assert _iguales(Decimal(0), "") is True
    assert _iguales(Decimal(0), Decimal(5)) is False
    assert _iguales(Decimal(5), None) is False
    assert _iguales(Decimal(5), "texto") is False
