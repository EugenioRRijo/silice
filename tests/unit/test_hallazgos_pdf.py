"""El informe de hallazgos de la auditoría de un libro en PDF (decisión P2 de Eugenio, 2026-11-19).

`pdf_de_hallazgos` dibuja un `InformeDeHallazgos` FICTICIO construido aquí. El oráculo es el texto
que extrae pdfplumber (otra biblioteca, no la que escribe el PDF): cada cifra con coma decimal y
punto de miles, cada tilde y cada hallazgo tal cual, el texto de la persona sin interpretarlo como
marcas (`<b>&`), el encabezado de la tabla en cada página y «Página n de N».
"""

from __future__ import annotations

import io
from decimal import Decimal

import pdfplumber

from aplicacion.hallazgos_pdf import (
    FilaDeHallazgo,
    InformeDeHallazgos,
    LineaDeTotal,
    dinero,
    nombre_del_pdf_de_hallazgos,
    pdf_de_hallazgos,
)

D = Decimal


def _texto(contenido: bytes) -> list[str]:
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        return [pagina.extract_text() or "" for pagina in pdf.pages]


def _fila(n: int, mensaje: str = "", impacto: str = "") -> FilaDeHallazgo:
    return FilaDeHallazgo(
        codigo=f"L{n}",
        severidad="Error" if n % 2 else "Advertencia",
        celda=f"APU-{n:02d}!F{n + 10}",
        descripcion=mensaje or f"Descripción del hallazgo número {n}",
        impacto=impacto,
        accion="a confirmar",
    )


def _informe(hallazgos: tuple[FilaDeHallazgo, ...], **cambios) -> InformeDeHallazgos:
    base = {
        "libro": "obra_ficticia.xlsx",
        "fecha_libro": "31/07/2026",
        "fecha_devolucion": "13/10/2026",
        "emitido": "19/11/2026",
        "veredicto": "No cumple",
        "conteo": ("1 error", "1 advertencia"),
        "totales": (
            LineaDeTotal("Subtotal sin IVA", "4.358,21", "4.203,93"),
            LineaDeTotal("Total general", "5.055,52", "4.876,56"),
        ),
        "hallazgos": hallazgos,
    }
    return InformeDeHallazgos(**{**base, **cambios})


def test_el_informe_trae_el_libro_las_fechas_el_veredicto_y_las_cifras_con_coma():
    texto = "\n".join(_texto(pdf_de_hallazgos(_informe((_fila(1, impacto="1.234,57"),)))))
    for esperado in (
        "Hallazgos de la auditoría",
        "obra_ficticia.xlsx",
        "31/07/2026",
        "13/10/2026",
        "19/11/2026",
        "No cumple",
        "1 error",
        "1 advertencia",
        "Subtotal sin IVA",
        "4.358,21",
        "4.203,93",
        "Total general",
        "5.055,52",
        "4.876,56",
    ):
        assert esperado in texto, esperado


def test_cada_hallazgo_sale_con_su_regla_su_celda_su_descripcion_y_su_impacto():
    filas = (_fila(1, impacto="1.234,57"), _fila(2, "El CD omite equipos (15 %)"))
    texto = "\n".join(_texto(pdf_de_hallazgos(_informe(filas))))
    for esperado in ("L1", "APU-01!F11", "Descripción del hallazgo número 1", "1.234,57"):
        assert esperado in texto, esperado
    for esperado in ("L2", "APU-02!F12", "El CD omite equipos (15", "a confirmar"):
        assert esperado in texto, esperado


def test_el_texto_de_la_persona_no_se_interpreta_como_marcas():
    texto = "\n".join(_texto(pdf_de_hallazgos(_informe((_fila(1, "<b>negrita</b> & «m³»"),)))))
    assert "<b>negrita</b>" in texto
    assert "&" in texto
    assert "m³" in texto


def test_sin_hallazgos_el_informe_lo_dice():
    texto = "\n".join(
        _texto(
            pdf_de_hallazgos(_informe((), veredicto="Cumple", conteo=("0 hallazgos",), totales=()))
        )
    )
    assert "Cumple" in texto
    assert "El libro no tiene hallazgos." in texto


def test_con_muchos_hallazgos_el_encabezado_se_repite_y_cada_pagina_se_numera():
    filas = tuple(_fila(n) for n in range(1, 121))
    paginas = _texto(pdf_de_hallazgos(_informe(filas)))
    assert len(paginas) >= 3
    for numero, pagina in enumerate(paginas, start=1):
        assert "Regla" in pagina and "Celda" in pagina  # el encabezado, en cada página
        assert f"Página {numero} de {len(paginas)}" in pagina
    todo = "\n".join(paginas)
    assert "L1 " in todo and "L120" in todo  # ninguno se pierde entre páginas


def test_dinero_escribe_al_alza_con_coma_y_punto_de_miles():
    assert dinero(D("1234.565")) == "1.234,57"
    assert dinero(D("0.125")) == "0,13"
    assert dinero(D("-0.001")) == "0,00"  # nunca «-0,00»
    assert dinero(D("5055.52157")) == "5.055,52"


def test_el_nombre_del_pdf_es_seguro_y_acotado():
    assert nombre_del_pdf_de_hallazgos("obra_ficticia.xlsx") == "hallazgos_obra_ficticia.pdf"
    nombre = nombre_del_pdf_de_hallazgos('Obra «A»/..\\x "2026".xlsx')
    assert nombre == "hallazgos_Obra__A__.._x__2026_.pdf"
    assert nombre_del_pdf_de_hallazgos("") == "hallazgos_libro.pdf"
    assert len(nombre_del_pdf_de_hallazgos("a" * 500 + ".xlsx")) <= len("hallazgos_.pdf") + 100
