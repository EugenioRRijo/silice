"""El «Qué hacer» de cada hallazgo y de cada alerta de precio (B2, ficha-b2 §3.3; acta, D8).

Es una capa de **presentación** sobre lo que las reglas ya informan: no cambia ninguna regla ni su
texto. Oráculos no circulares: la lista de códigos esperados está escrita aquí, a mano, desde la
especificación (reglas L1 a L11 y F1 del libro de la empresa, R1 a R7 del núcleo y las cuatro
alertas de precio de `fusion/alertas.py`), y las frases con que el servidor dice «no hay nada que
avisar» se comprueban contra una alerta real.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest

from adapters.hoja_empresa.lector import leer_libro
from aplicacion import que_hacer as qh
from aplicacion.nombres_reglas import NOMBRES_DE_REGLAS
from fusion.alertas import (
    TIPO_BS,
    TIPO_EMPRESA,
    TIPO_SIN_FUENTE,
    TIPO_VERSION,
    ContextoPrecios,
    alertas_de_precios,
)
from tests.fixtures.libros_empresa import libro_limpio

# Lo que un libro puede emitir (spec 1.5 §3 y UC-05), escrito a mano.
CODIGOS_DEL_LIBRO = (
    *(f"L{n}" for n in range(1, 12)),
    "F1",
    *(f"R{n}" for n in range(1, 8)),
)
TIPOS_DE_ALERTA = (TIPO_SIN_FUENTE, TIPO_EMPRESA, TIPO_VERSION, TIPO_BS)

# Trato de tú: la guardia de interfaz lo vigila en el front; aquí, en el servidor.
TUTEO = re.compile(
    r"\b(tú|tu|tus|puedes|tienes|debes|revisa|corrige|abre|anota|compara|pulsa|escribe|usa|pide)\b",
    re.IGNORECASE,
)
JERGA = re.compile(r"\b(regex|sha|json|api|stack|null|none)\b", re.IGNORECASE)


@pytest.mark.parametrize("codigo", CODIGOS_DEL_LIBRO)
def test_cada_regla_del_libro_tiene_su_que_hacer_propio(codigo: str) -> None:
    q = qh.que_hacer_de_regla(codigo)
    assert q.codigo == codigo
    assert q.generico is False
    assert q.titulo == NOMBRES_DE_REGLAS[codigo]
    assert q.significa.strip().endswith(".")
    assert q.que_hacer.strip().endswith(".")
    assert 40 <= len(q.que_hacer) <= 420


def test_los_textos_estan_en_usted_y_sin_jerga() -> None:
    todos = [qh.que_hacer_de_regla(c) for c in CODIGOS_DEL_LIBRO]
    todos += [qh.que_hacer_de_alerta(t) for t in TIPOS_DE_ALERTA]
    todos.append(qh.GENERICO)
    for q in todos:
        for texto in (q.significa, q.que_hacer):
            assert TUTEO.search(texto) is None, (q.codigo, texto)
            assert JERGA.search(texto) is None, (q.codigo, texto)


def test_los_que_hacer_no_se_repiten() -> None:
    textos = [qh.que_hacer_de_regla(c).que_hacer for c in CODIGOS_DEL_LIBRO]
    textos += [qh.que_hacer_de_alerta(t).que_hacer for t in TIPOS_DE_ALERTA]
    assert len(set(textos)) == len(textos)


def test_una_regla_que_no_se_conoce_da_el_generico_y_lo_dice() -> None:
    q = qh.que_hacer_de_regla("ZZ9")
    assert q.generico is True
    assert q.codigo == "ZZ9"
    assert q.que_hacer == qh.GENERICO.que_hacer
    assert qh.GENERICO.generico is True


def test_los_codigos_estables_tienen_una_forma_fija() -> None:
    forma = re.compile(r"^(L\d+|R\d+|F\d+|alerta:[a-z]+(-[a-z]+)*)$")
    codigos = [qh.que_hacer_de_regla(c).codigo for c in CODIGOS_DEL_LIBRO]
    codigos += [qh.que_hacer_de_alerta(t).codigo for t in TIPOS_DE_ALERTA]
    assert all(forma.match(c) for c in codigos), codigos
    assert len(set(codigos)) == len(codigos)


def test_las_alertas_cubren_los_cuatro_tipos_de_fusion() -> None:
    assert set(qh.TIPOS_DE_ALERTA) == set(TIPOS_DE_ALERTA)
    assert qh.que_hacer_de_alerta(TIPO_BS).codigo == "alerta:usd-bs"
    assert qh.que_hacer_de_alerta(TIPO_SIN_FUENTE).codigo == "alerta:sin-fuente"
    assert qh.que_hacer_de_alerta(TIPO_EMPRESA).codigo == "alerta:base-de-la-empresa"
    assert qh.que_hacer_de_alerta(TIPO_VERSION).codigo == "alerta:otra-version"
    assert qh.que_hacer_de_alerta("tipo que no existe").generico is True


def test_el_titulo_de_una_alerta_es_su_nombre_llano() -> None:
    assert qh.que_hacer_de_alerta(TIPO_SIN_FUENTE).titulo == "Sin fuente"
    assert qh.que_hacer_de_alerta(TIPO_EMPRESA).titulo == "Base de la empresa"
    assert qh.que_hacer_de_alerta(TIPO_VERSION).titulo == "Otra versión"
    assert qh.que_hacer_de_alerta(TIPO_BS).titulo == "USD-Bs"


def test_la_frase_de_sin_aviso_es_la_que_dice_fusion_cuando_esta_dentro_del_umbral() -> None:
    libro = leer_libro(libro_limpio().datos, "limpio.xlsx")
    f_libro, f_dev = date(2026, 7, 31), date(2026, 10, 13)
    tasas = {f_libro: Decimal("100"), f_dev: Decimal("104.99")}  # 4,99 %: dentro del 5 %
    contexto = ContextoPrecios(tasa_en=tasas.get)
    bs = [a for a in alertas_de_precios(libro, f_libro, f_dev, contexto) if a.tipo == TIPO_BS]
    frases = qh.que_hacer_de_alerta(TIPO_BS).sin_aviso_si
    assert frases, "USD-Bs debe declarar cuándo no hay nada que avisar"
    assert all(any(f in a.mensaje for f in frases) for a in bs)


def test_la_frase_de_sin_aviso_no_aparece_cuando_pasa_del_umbral() -> None:
    libro = leer_libro(libro_limpio().datos, "limpio.xlsx")
    f_libro, f_dev = date(2026, 7, 31), date(2026, 10, 13)
    tasas = {f_libro: Decimal("100"), f_dev: Decimal("105")}  # 5 %: pasa
    contexto = ContextoPrecios(tasa_en=tasas.get)
    bs = [a for a in alertas_de_precios(libro, f_libro, f_dev, contexto) if a.tipo == TIPO_BS]
    frases = qh.que_hacer_de_alerta(TIPO_BS).sin_aviso_si
    assert not any(f in a.mensaje for a in bs for f in frases)


def test_las_demas_alertas_siempre_avisan() -> None:
    for tipo in (TIPO_SIN_FUENTE, TIPO_EMPRESA, TIPO_VERSION):
        assert qh.que_hacer_de_alerta(tipo).sin_aviso_si == ()


def test_el_catalogo_se_sirve_con_reglas_alertas_y_generico() -> None:
    c = qh.catalogo()
    assert set(c) == {"reglas", "alertas", "generico"}
    assert set(c["reglas"]) == set(CODIGOS_DEL_LIBRO)
    assert set(c["alertas"]) == set(TIPOS_DE_ALERTA)
    assert c["generico"]["generico"] is True
    assert c["reglas"]["L4"] == {
        "codigo": "L4",
        "titulo": "Componente fuera del total",
        "significa": qh.que_hacer_de_regla("L4").significa,
        "que_hacer": qh.que_hacer_de_regla("L4").que_hacer,
        "generico": False,
        "sin_aviso_si": [],
    }
    assert c["alertas"][TIPO_BS]["sin_aviso_si"] == list(
        qh.que_hacer_de_alerta(TIPO_BS).sin_aviso_si
    )


# --- Auditoría independiente antes de medicion-v1 (#5 y #6) ---------------------------------------


def test_l5_cubre_tambien_las_celdas_que_dan_error_al_calcular() -> None:
    """L5 informa #REF! y vínculos externos, pero también #DIV/0! o #VALOR! en la cadena de montos
    (`adapters/hoja_empresa/reglas_calculo.py`, `l5_celdas_con_error`): el texto lo dice."""
    q = qh.que_hacer_de_regla("L5")
    assert "o una celda da error al calcular" in q.significa
    # Como los muestra Excel en español (en el archivo se guardan en inglés: #DIV/0!, #VALUE!).
    assert "#¡DIV/0!" in q.que_hacer and "#¡VALOR!" in q.que_hacer


@pytest.mark.parametrize("codigo", ["L6", "R6"])
def test_l6_y_r6_dicen_que_confirmar_y_no_que_decidir(codigo: str) -> None:
    """F-D7: el auditor no decide la intención de quien hizo el libro."""
    q = qh.que_hacer_de_regla(codigo)
    assert q.que_hacer.startswith("Confirme con quien hizo el libro si ")


def test_ninguna_guia_le_pide_al_auditor_que_decida() -> None:
    textos = [qh.que_hacer_de_regla(c) for c in CODIGOS_DEL_LIBRO]
    textos += [qh.que_hacer_de_alerta(t) for t in TIPOS_DE_ALERTA]
    decide = re.compile(r"\bdecida\b", re.IGNORECASE)
    assert [q.codigo for q in textos if decide.search(q.que_hacer)] == []
