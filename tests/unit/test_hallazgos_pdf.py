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
import pytest

from aplicacion import hallazgos_pdf
from aplicacion.hallazgos_pdf import (
    FilaDeHallazgo,
    InformeDeHallazgos,
    LineaDeTotal,
    conteo_por_severidad,
    dinero,
    nombre_del_pdf_de_hallazgos,
    pdf_de_hallazgos,
    severidad_escrita,
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
        "huella": "",
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


# --- Correcciones arbitradas (2026-11-19) ---


def _plano(contenido: bytes) -> str:
    """El texto del PDF sin saltos de línea: una cifra o una palabra partida en dos renglones no
    se encuentra."""
    return "".join(_texto(contenido))


def test_una_fila_mas_alta_que_la_pagina_no_tumba_el_pdf_y_se_acota_con_puntos():
    largo = "ABCDEFGHIJ" + "x" * 20_000  # sin un solo espacio donde partir
    palabras = " ".join(["palabra"] * 3_000)
    informe = _informe((_fila(1, largo), _fila(2, palabras)))
    contenido = pdf_de_hallazgos(informe)
    assert contenido.startswith(b"%PDF")
    texto = "\n".join(_texto(contenido))
    assert "ABCDEFGHIJ" in texto  # el inicio del texto se conserva
    assert "…" in texto
    assert "x" * 5_000 not in _plano(contenido)  # lo demás se acota


def test_aunque_el_tope_de_texto_no_acote_la_fila_se_parte_entre_paginas(monkeypatch):
    monkeypatch.setattr(hallazgos_pdf, "TOPE_DE_TEXTO", 100_000)
    contenido = pdf_de_hallazgos(_informe((_fila(1, "ABCDEFGHIJ" + "x" * 20_000),)))
    assert contenido.startswith(b"%PDF")
    assert "ABCDEFGHIJ" in "\n".join(_texto(contenido))


@pytest.mark.parametrize("cifra", ["-1.234.567,89", "10.000.000,00", "-0,13"])
def test_una_cifra_sale_entera_en_una_linea_con_su_signo(cifra):
    filas = tuple(_fila(n, impacto=cifra) for n in range(1, 6))
    contenido = pdf_de_hallazgos(
        _informe(filas, totales=(LineaDeTotal("Total general", cifra, "10.000.000,00"),))
    )
    for pagina in _texto(contenido):
        for linea in pagina.splitlines():
            if linea.startswith("L") and "APU-" in linea:
                assert cifra in linea, linea
    assert _texto(contenido)[0].count(cifra) >= 6  # cinco filas y el total


def test_dinero_reusa_el_redondeo_de_la_pantalla_y_no_cae_con_un_valor_enorme():
    assert dinero(D("1234.565")) == "1.234,57"
    assert dinero(D("-1234567.885")) == "-1.234.567,89"
    enorme = D("12345678901234567890123456789.125")  # no cabe en la precisión: exacto
    assert dinero(enorme) == "12.345.678.901.234.567.890.123.456.789,125"
    assert dinero(D("1E+40")) == "10.000.000.000.000.000.000.000.000.000.000.000.000.000"


def test_un_nombre_de_libro_enorme_no_pisa_el_numero_de_pagina():
    nombre = "libro_" + "z" * 400 + ".xlsx"
    contenido = pdf_de_hallazgos(_informe((_fila(1),), libro=nombre))
    plano = _plano(contenido)
    assert "Página 1 de 1" in plano  # entera: el pie no la pisa
    assert "Sílice · libro_" in plano and "hallazgos de la auditoría" in plano
    assert "…" in plano
    assert "z" * 160 not in plano  # ni en el subtítulo ni en el pie


def test_con_mas_de_dos_mil_hallazgos_muestra_el_tope_y_dice_cuantos_faltan(monkeypatch):
    assert hallazgos_pdf.MAX_FILAS == 2_000
    monkeypatch.setattr(hallazgos_pdf, "MAX_FILAS", 30)
    filas = tuple(_fila(n) for n in range(1, 46))
    texto = "\n".join(_texto(pdf_de_hallazgos(_informe(filas))))
    assert "y 15 hallazgos más; véalos en Sílice" in texto
    assert "L30 " in texto and "L31 " not in texto


def test_con_un_hallazgo_de_mas_el_aviso_va_en_singular(monkeypatch):
    monkeypatch.setattr(hallazgos_pdf, "MAX_FILAS", 3)
    filas = tuple(_fila(n) for n in range(1, 5))
    texto = "\n".join(_texto(pdf_de_hallazgos(_informe(filas))))
    assert "y 1 hallazgo más; véalo en Sílice" in texto


def test_el_pdf_imprime_la_huella_abreviada_del_libro():
    texto = "\n".join(_texto(pdf_de_hallazgos(_informe((), huella="abcdef012345"))))
    assert "Huella del libro (SHA-256): abcdef012345" in texto


# severidad_escrita y conteo_por_severidad: salidas escritas a mano


def test_severidad_escrita_como_la_interfaz_y_una_desconocida_tal_cual():
    assert [severidad_escrita(s) for s in ("CRITICO", "ERROR", "ADVERTENCIA", "INFO")] == [
        "Crítico",
        "Error",
        "Advertencia",
        "Información",
    ]
    assert severidad_escrita("RARA") == "RARA"


def test_conteo_en_singular_plural_y_de_la_mas_a_la_menos_grave():
    assert conteo_por_severidad(["INFO", "ERROR", "CRITICO"]) == (
        "1 crítico",
        "1 error",
        "1 aviso informativo",
    )
    assert conteo_por_severidad(["INFO", "INFO", "ERROR", "ERROR", "ADVERTENCIA"]) == (
        "2 errores",
        "1 advertencia",
        "2 avisos informativos",
    )


def test_sin_hallazgos_el_conteo_lo_dice():
    assert conteo_por_severidad([]) == ("Sin hallazgos",)


def test_una_severidad_desconocida_se_cuenta_al_final_y_no_se_pierde():
    assert conteo_por_severidad(["RARA"]) == ("1 con severidad «RARA»",)
    assert conteo_por_severidad(["RARA", "ERROR", "RARA"]) == (
        "1 error",
        "2 con severidad «RARA»",
    )
