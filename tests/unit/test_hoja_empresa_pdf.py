"""PDF de presupuestos de la empresa: reglas L10 y L11 y rechazos del PDF (Silice 1.5, RF-105,
RNF-21; spec 1.5 §3 y errata 6 y 7).

- **L10** (`leer_pdf_simple` + `reglas_pdf_simple`): un PDF simple, sin modelo de cálculo, se
  revisa consigo mismo. Hay una prueba por subtipo con el error SEMBRADO y su frontera
  (`TOLERANCIA` = 0,005 USD: 0,005 no es hallazgo, 0,006 sí), y el CONJUNTO EXACTO (regla,
  severidad, subtipo, origen, impacto) de un PDF limpio (vacío) y de uno con varios errores.
- **L11** (`leer_totales_impresos` + `cotejar_con_libro`): el bloque de totales del PDF impreso
  desde el libro contra los totales del libro sintético; con dos bloques se coteja el ÚLTIMO
  (errata 7).
- **RNF-21**: cabecera `%PDF-` en el primer kilobyte, `/Encrypt`, `/JavaScript`, páginas
  (60 pasa / 61 falla, también cuando el `/Count` miente) y tamaño (`MAX_BYTES_PDF`).
- **Errata 6** (`fusion.proceso._leer_pdf`, `procesar_libro`, `auditar_pdf_simple`): si el PDF
  trae el bloque de totales del impreso se coteja con L11; si no, y trae tablas, es un PDF simple
  (L10).

Los PDF se GENERAN aquí con reportlab (extra `informes`): son ficticios, sin red y sin leer ningún
PDF del repositorio. Imitan la forma que describe `adapters/hoja_empresa/pdf.py`: una página
"COMPUTOS MÉTRICOS" (Items, Descripción, Unidad, Cantidad, "Total computos métricos") y una de
presupuesto (además Precio Unitario y Total, "TOTAL PRESUPUESTO"), notas con `*`, renglones
resaltados en amarillo. Sin cuadriculado: el lector agrupa las filas por líneas de texto.

Oráculo: las cifras impresas son literales de la prueba y lo esperado se calcula a mano en el
comentario de cada caso (p. ej. 5 × 289,00 = 1 445,00; impreso 1 446,65 -> +1,65). Para L11, la
memoria de cálculo a mano del libro limpio (`MEMORIA`: 4 358,20825 / 697,31332 / 5 055,52157).
Los subtipos se comparan con su texto literal, no con las constantes del módulo.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

import pytest
from reportlab.pdfgen import canvas

from adapters.hoja_empresa import pdf as modulo_pdf
from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.modelo import LibroNoInterpretable
from adapters.hoja_empresa.pdf import (
    MAX_BYTES_PDF,
    MAX_PAGINAS_PDF,
    TOLERANCIA,
    PdfSimple,
    RenglonPdf,
    TotalesImpresos,
    cotejar_con_libro,
    leer_pdf_simple,
    leer_totales_impresos,
    reglas_pdf_simple,
)
from core.contracts.verificacion import Hallazgo, Severidad
from fusion.proceso import _leer_pdf, auditar_pdf_simple, procesar_libro
from tests.fixtures.libros_empresa import MEMORIA, D, libro_limpio

ERROR, ADVERTENCIA, INFO = Severidad.ERROR, Severidad.ADVERTENCIA, Severidad.INFO

# Subtipos de L10 (texto literal del informe, al inicio de la descripción).
UNIDADES = "suma de unidades distintas"
INCOHERENTE = "unidad × cantidad × precio incoherente"
ARITMETICA = "aritmética de fila"
COMPUTOS = "cómputos ≠ presupuesto"
PENDIENTE = "precio pendiente entregado como firme"
NOTA = "nota que contradice el total"
SUMA = "suma de renglones ≠ total impreso"

NOMBRE = "presupuesto_ficticio.pdf"
P1 = f"PDF:{NOMBRE}:p1"  # página de cómputos
P2 = f"PDF:{NOMBRE}:p2"  # página de presupuesto
NOTAS = f"PDF:{NOMBRE}:notas"


# --- Generador de PDF ficticios -------------------------------------------------------------------


@dataclass(frozen=True)
class Fila:
    """Un renglón tal como se imprime (texto literal en cada columna)."""

    item: str
    descripcion: str
    unidad: str
    cantidad: str
    precio: str = ""
    total: str = ""
    resaltado: bool = False


# Abscisas de cada columna (pt). La cabecera "Items" queda a la izquierda del número de ítem y la
# de cada columna encima de su dato: el lector toma las fronteras de la cabecera.
_X = {"item": 45, "descripcion": 90, "unidad": 300, "cantidad": 360, "precio": 430, "total": 510}
#: Líneas verticales del cuadriculado: entre la cabecera de una columna y la de la siguiente.
_VERTICALES = (85, 295, 355, 425, 505)


def _tabla(
    c: canvas.Canvas,
    titulo: str,
    filas: Sequence[Fila],
    rotulo_total: str,
    total: str | None,
    notas: Sequence[str],
    con_precio: bool,
    cuadriculado: bool = False,
) -> None:
    c.setFont("Helvetica", 10)
    c.drawString(40, 760, titulo)
    c.drawString(40, 740, "001 Fecha: 18/05/2026")
    y = 700
    c.drawString(40, y, "Items")
    c.drawString(_X["descripcion"], y, "Descripción")
    c.drawString(_X["unidad"], y, "Unidad")
    c.drawString(_X["cantidad"], y, "Cantidad")
    if con_precio:
        c.drawString(_X["precio"], y, "Precio")
        c.drawString(_X["precio"], y - 10, "Unitario")
        c.drawString(_X["total"], y, "Total ($)")
    y -= 30
    y_inicio = y + 11
    for f in filas:
        if cuadriculado:  # borde superior de la fila, de la columna de ítem a la de total
            c.line(38, y + 11, 580, y + 11)
        if f.resaltado:  # rectángulo amarillo de relleno detrás de la fila
            c.setFillColorRGB(1, 1, 0)
            c.rect(38, y - 3, 540, 12, stroke=0, fill=1)
            c.setFillColorRGB(0, 0, 0)
        c.drawString(_X["item"], y, f.item)
        c.drawString(_X["descripcion"], y, f.descripcion)
        c.drawString(_X["unidad"], y, f.unidad)
        c.drawString(_X["cantidad"], y, f.cantidad)
        if con_precio:
            c.drawString(_X["precio"], y, f.precio)
            c.drawString(_X["total"], y, f.total)
        y -= 16
    if cuadriculado:
        c.line(38, y + 11, 580, y + 11)  # borde inferior de la última fila
        for x in _VERTICALES[: 5 if con_precio else 3]:
            c.line(x, y + 11, x, y_inicio)
    if total is not None:
        c.drawString(_X["descripcion"], y, rotulo_total)
        c.drawString(_X["total"] if con_precio else _X["cantidad"], y, total)
    y -= 30
    for n in notas:
        c.drawString(40, y, "* " + n)
        y -= 16
    c.showPage()


def pdf_simple(
    computos: Sequence[Fila],
    total_computos: str | None,
    presupuesto: Sequence[Fila],
    total_presupuesto: str | None,
    notas: Sequence[str] = (),
    cuadriculado: bool = False,
) -> bytes:
    """PDF simple de dos páginas: cómputos (p. 1) y presupuesto con sus notas (p. 2). Una lista
    vacía omite esa página. Con `cuadriculado`, las filas van entre líneas (otra lectura del
    lector: filas por bandas y columnas por las verticales)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    if computos:
        _tabla(
            c,
            "COMPUTOS MÉTRICOS",
            computos,
            "Total computos métricos",
            total_computos,
            (),
            False,
            cuadriculado,
        )
    if presupuesto:
        _tabla(
            c,
            "PRESUPUESTO",
            presupuesto,
            "TOTAL PRESUPUESTO",
            total_presupuesto,
            notas,
            True,
            cuadriculado,
        )
    c.save()
    return buf.getvalue()


def pdf_impreso(bloques: Sequence[tuple[str, str | None, str | None, str | None]]) -> bytes:
    """PDF "impreso desde el libro": cada bloque es (rótulo OPCIÓN o "", sin IVA, IVA, total) en
    su propia página; None omite esa línea."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for opcion, subtotal, iva, total in bloques:
        c.setFont("Helvetica", 10)
        y = 760
        c.drawString(40, y, "OBRA FICTICIA DE PRUEBA - RESUMEN")
        y -= 30
        if opcion:
            c.drawString(40, y, opcion)
            y -= 20
        for rotulo, monto in (
            ("TOTAL COSTO DE LA OBRA (SUB-TOTAL SIN IVA)", subtotal),
            ("IVA 16%", iva),
            ("TOTAL PRESUPUESTO (USD)", total),
        ):
            if monto is not None:
                c.drawString(40, y, rotulo)
                c.drawString(400, y, monto)
                y -= 16
        c.showPage()
    c.save()
    return buf.getvalue()


def paginas_en_blanco(n: int, **opciones: object) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, **opciones)
    for i in range(n):
        c.drawString(40, 700, f"Hoja {i + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


def clave(h: Hallazgo) -> tuple[str, Severidad, str, tuple[str, ...], Decimal | None]:
    """(regla, severidad, subtipo, origen, impacto). El subtipo es lo que precede al primer «: »."""
    return (h.regla, h.severidad, h.descripcion.split(": ", 1)[0], h.origen_ids, h.impacto)


def hallazgos_l10(
    datos: bytes,
) -> list[tuple[str, Severidad, str, tuple[str, ...], Decimal | None]]:
    return sorted(
        (clave(h) for h in reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))),
        key=repr,
    )


def conjunto(*esperados: tuple) -> list[tuple]:
    return sorted(esperados, key=repr)


# --- PDF limpio (base de los sembrados) -----------------------------------------------------------
#
# Cómputos: 5 m2 de friso + 1 m2 de pintura = 6.
# Presupuesto: 5 × 289,00 = 1 445,00; 1 × 125,01 = 125,01; suma 1 570,01 = TOTAL PRESUPUESTO.

FRISO_C = Fila("1", "Friso liso de paredes", "m2", "5")
PINTURA_C = Fila("2", "Pintura de caucho", "m2", "1")
FRISO_P = Fila("1", "Friso liso de paredes", "m2", "5", "289.00", "1,445.00")
PINTURA_P = Fila("2", "Pintura de caucho", "m2", "1", "125.01", "125.01")


def limpio(**cambios: object) -> bytes:
    args: dict[str, object] = {
        "computos": (FRISO_C, PINTURA_C),
        "total_computos": "6",
        "presupuesto": (FRISO_P, PINTURA_P),
        "total_presupuesto": "1,570.01",
        "notas": (),
    }
    args.update(cambios)
    return pdf_simple(**args)  # type: ignore[arg-type]


# --- Lectura: el generador produce lo que se quiso imprimir ---------------------------------------


def test_leer_pdf_simple_reconstruye_los_renglones_exactos():
    datos = limpio(notas=("Precios sujetos a cambio", "Validez de la oferta: 15 días"))
    pdf = leer_pdf_simple(datos, NOMBRE)
    assert pdf.computos == (
        RenglonPdf(1, "1", "Friso liso de paredes", "m2", D("5"), "", None, None, False),
        RenglonPdf(1, "2", "Pintura de caucho", "m2", D("1"), "", None, None, False),
    )
    assert pdf.presupuesto == (
        RenglonPdf(
            2, "1", "Friso liso de paredes", "m2", D("5"), "289.00", D("289"), D("1445"), False
        ),
        RenglonPdf(
            2, "2", "Pintura de caucho", "m2", D("1"), "125.01", D("125.01"), D("125.01"), False
        ),
    )
    assert pdf.total_computos == D("6")
    assert pdf.total_impreso == D("1570.01")
    assert pdf.notas == ("Precios sujetos a cambio", "Validez de la oferta: 15 días")
    assert (pdf.numero, pdf.fecha) == ("001", "18/05/2026")
    assert pdf.nombre == NOMBRE
    assert pdf.sha256 == hashlib.sha256(datos).hexdigest()
    assert all(isinstance(r.cantidad, Decimal) for r in pdf.computos + pdf.presupuesto)


def test_leer_pdf_simple_marca_el_renglon_resaltado_y_guarda_la_expresion_como_texto():
    datos = limpio(
        presupuesto=(
            FRISO_P,
            Fila("2", "Pintura de caucho", "m2", "1", "3*99.75", "299.25", resaltado=True),
        )
    )
    pdf = leer_pdf_simple(datos, NOMBRE)
    friso, pintura = pdf.presupuesto
    assert (friso.resaltado, pintura.resaltado) == (False, True)
    assert pintura.precio_texto == "3*99.75"
    assert pintura.precio is None  # una expresión no es un precio unitario
    assert pintura.total == D("299.25")


def test_leer_pdf_simple_con_cuadriculado_lee_lo_mismo():
    # Mismo contenido con líneas entre filas y entre columnas: el lector toma las filas por
    # bandas y las fronteras de columna por las verticales, y debe reconstruir los mismos
    # renglones (también el resaltado).
    filas_p = (FRISO_P, replace(PINTURA_P, resaltado=True))
    sin = leer_pdf_simple(limpio(presupuesto=filas_p), NOMBRE)
    con = leer_pdf_simple(limpio(presupuesto=filas_p, cuadriculado=True), NOMBRE)
    assert con.computos == sin.computos
    assert con.presupuesto == sin.presupuesto
    assert (con.total_computos, con.total_impreso) == (D("6"), D("1570.01"))
    assert [r.resaltado for r in con.presupuesto] == [False, True]


def test_pdf_limpio_da_el_conjunto_vacio():
    assert hallazgos_l10(limpio()) == []


# --- L10: suma de unidades distintas --------------------------------------------------------------


def test_l10_unidades_distintas_en_el_total_de_computos_es_advertencia():
    # Cómputos: 90 m de cable + 4 und de tomas = "94" (una cifra sin unidad).
    # Presupuesto cuadrado: 90 × 1,50 = 135,00; 4 × 8,25 = 33,00; total 168,00.
    datos = pdf_simple(
        (Fila("1", "Cable THW 12", "m", "90"), Fila("2", "Toma corriente doble", "und", "4")),
        "94",
        (
            Fila("1", "Cable THW 12", "m", "90", "1.50", "135.00"),
            Fila("2", "Toma corriente doble", "und", "4", "8.25", "33.00"),
        ),
        "168.00",
    )
    assert hallazgos_l10(datos) == [("L10", ADVERTENCIA, UNIDADES, (f"{P1}:total",), None)]
    (h,) = reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))
    assert h.valor_observado == D("94")


def test_l10_una_sola_unidad_en_los_computos_no_es_hallazgo():
    datos = pdf_simple(
        (Fila("1", "Cable THW 12", "m", "90"), Fila("2", "Cable THW 10", "m", "4")),
        "94",
        (
            Fila("1", "Cable THW 12", "m", "90", "1.50", "135.00"),
            Fila("2", "Cable THW 10", "m", "4", "8.25", "33.00"),
        ),
        "168.00",
    )
    assert hallazgos_l10(datos) == []


# --- L10: aritmética de fila ----------------------------------------------------------------------


def test_l10_aritmetica_de_fila_es_error_con_impacto():
    # 5 × 289,00 = 1 445,00 y el PDF imprime 1 446,65 -> +1,65. TOTAL = 1 446,65 + 125,01.
    datos = limpio(
        presupuesto=(
            Fila("1", "Friso liso de paredes", "m2", "5", "289.00", "1,446.65"),
            PINTURA_P,
        ),
        total_presupuesto="1,571.66",
    )
    assert hallazgos_l10(datos) == [("L10", ERROR, ARITMETICA, (f"{P2}:item1",), D("1.65"))]
    (h,) = reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))
    assert (h.valor_observado, h.valor_esperado) == (D("1446.65"), D("1445.00"))


@pytest.mark.parametrize(
    ("total_fila", "total_doc", "esperado"),
    [
        # 1 445,005 − 1 445,00 = 0,005 = TOLERANCIA: redondeo de impresión, no hallazgo.
        ("1,445.005", "1,570.015", []),
        # 0,006 > 0,005: ERROR con impacto +0,006.
        (
            "1,445.006",
            "1,570.016",
            [("L10", ERROR, ARITMETICA, (f"{P2}:item1",), D("0.006"))],
        ),
    ],
)
def test_l10_aritmetica_de_fila_frontera_de_medio_centimo(total_fila, total_doc, esperado):
    assert Decimal("0.005") == TOLERANCIA
    datos = limpio(
        presupuesto=(
            Fila("1", "Friso liso de paredes", "m2", "5", "289.00", total_fila),
            PINTURA_P,
        ),
        total_presupuesto=total_doc,
    )
    assert hallazgos_l10(datos) == esperado


# --- L10: unidad × cantidad × precio incoherente --------------------------------------------------


def _cable(unidad: str, precio: str, total: str) -> bytes:
    return pdf_simple(
        (Fila("1", "Cable THW 12 negro", unidad, "90"),),
        "90",
        (Fila("1", "Cable THW 12 negro", unidad, "90", precio, total),),
        total,
    )


def test_l10_metros_por_precio_de_pieza_es_incoherencia_sin_impacto():
    # 90 m × 99,75 = 8 977,50, pero 299,25 = 3 × 99,75: el precio es por rollo. ERROR sin impacto.
    datos = _cable("m", "99.75", "299.25")
    assert hallazgos_l10(datos) == [("L10", ERROR, INCOHERENTE, (f"{P2}:item1",), None)]
    (h,) = reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))
    assert (h.valor_observado, h.valor_esperado) == (D("299.25"), D("8977.50"))


def test_l10_misma_fila_en_unidades_no_de_longitud_es_aritmetica():
    # Con "und" no hay lectura por pieza: 299,25 − 90 × 99,75 = 299,25 − 8 977,50 = −8 678,25.
    datos = _cable("und", "99.75", "299.25")
    assert hallazgos_l10(datos) == [("L10", ERROR, ARITMETICA, (f"{P2}:item1",), D("-8678.25"))]


def test_l10_precio_escrito_como_expresion_es_incoherencia():
    # «3*99.75» = 299,25 = total (la aritmética cuadra), pero cobra 3 unidades y no 90 m.
    # Con 90 m a 99,75 serían 8 977,50.
    datos = _cable("m", "3*99.75", "299.25")
    assert hallazgos_l10(datos) == [("L10", ERROR, INCOHERENTE, (f"{P2}:item1",), None)]
    (h,) = reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))
    assert h.valor_esperado == D("8977.50")


def test_l10_expresion_que_tampoco_cuadra_da_incoherencia_y_aritmetica():
    # «3*99.75» = 299,25 y el PDF imprime 300,00 -> +0,75.
    datos = _cable("m", "3*99.75", "300.00")
    assert hallazgos_l10(datos) == conjunto(
        ("L10", ERROR, INCOHERENTE, (f"{P2}:item1",), None),
        ("L10", ERROR, ARITMETICA, (f"{P2}:item1",), D("0.75")),
    )


# --- L10: cómputos ≠ presupuesto ------------------------------------------------------------------


def test_l10_cantidad_distinta_con_fila_que_cuadra_da_impacto():
    # Cómputos 80 m2, presupuesto 90 m2 × 12,50 = 1 125,00 (cuadra) -> (90 − 80) × 12,50 = 125,00.
    datos = pdf_simple(
        (Fila("1", "Friso liso de paredes", "m2", "80"),),
        "80",
        (Fila("1", "Friso liso de paredes", "m2", "90", "12.50", "1,125.00"),),
        "1,125.00",
    )
    assert hallazgos_l10(datos) == [
        ("L10", ERROR, COMPUTOS, (f"{P1}:item1", f"{P2}:item1"), D("125.00"))
    ]
    (h,) = reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))
    assert (h.valor_observado, h.valor_esperado) == (D("90"), D("80"))


def test_l10_cantidad_distinta_con_fila_que_no_cuadra_no_tiene_impacto():
    # 90 × 12,50 = 1 125,00 e imprime 1 130,00 (+5,00): el precio no es por la unidad impresa,
    # así que la diferencia de cómputos queda sin impacto.
    datos = pdf_simple(
        (Fila("1", "Friso liso de paredes", "m2", "80"),),
        "80",
        (Fila("1", "Friso liso de paredes", "m2", "90", "12.50", "1,130.00"),),
        "1,130.00",
    )
    assert hallazgos_l10(datos) == conjunto(
        ("L10", ERROR, ARITMETICA, (f"{P2}:item1",), D("5.00")),
        ("L10", ERROR, COMPUTOS, (f"{P1}:item1", f"{P2}:item1"), None),
    )


def test_l10_renglones_sin_pareja_son_advertencia_en_cada_lado():
    # Cómputos: friso 5 + demolición 4 = 9. Presupuesto: friso 1 445,00 + limpieza 1 × 40,00.
    datos = pdf_simple(
        (FRISO_C, Fila("2", "Demolición de bloques", "m2", "4")),
        "9",
        (FRISO_P, Fila("2", "Limpieza final de obra", "sg", "1", "40.00", "40.00")),
        "1,485.00",
    )
    assert hallazgos_l10(datos) == conjunto(
        ("L10", ADVERTENCIA, COMPUTOS, (f"{P1}:item2",), None),
        ("L10", ADVERTENCIA, COMPUTOS, (f"{P2}:item2",), None),
    )


def test_l10_unidad_distinta_en_el_par_es_advertencia():
    datos = limpio(computos=(FRISO_C, Fila("2", "Pintura de caucho", "gal", "1")))
    assert hallazgos_l10(datos) == [
        ("L10", ADVERTENCIA, COMPUTOS, (f"{P1}:item2", f"{P2}:item2"), None),
        # gal + m2 en el total de cómputos: también suma unidades distintas.
        ("L10", ADVERTENCIA, UNIDADES, (f"{P1}:total",), None),
    ]


def test_l10_descripcion_truncada_en_el_presupuesto_se_empareja():
    # La página de presupuesto trunca la descripción: «… Cobra» es prefijo de «… Cobra (Blister)».
    datos = pdf_simple(
        (Fila("1", "Teipe Eléctrico Negro Cobra (Blister)", "und", "3"),),
        "3",
        (Fila("1", "Teipe Eléctrico Negro Cobra", "und", "3", "2.10", "6.30"),),
        "6.30",
    )
    assert hallazgos_l10(datos) == []


# --- L10: precio "en veremos" y resaltado ---------------------------------------------------------


def test_l10_precio_en_veremos_con_renglon_resaltado_es_advertencia():
    datos = limpio(
        presupuesto=(FRISO_P, replace(PINTURA_P, resaltado=True)),
        notas=("El precio de la pintura está en veremos",),
    )
    assert hallazgos_l10(datos) == [("L10", ADVERTENCIA, PENDIENTE, (f"{P2}:item2",), None)]
    (h,) = reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))
    assert h.valor_observado == D("125.01")


def test_l10_resaltado_sin_nota_es_info():
    datos = limpio(presupuesto=(FRISO_P, replace(PINTURA_P, resaltado=True)))
    assert hallazgos_l10(datos) == [("L10", INFO, PENDIENTE, (f"{P2}:item2",), None)]


def test_l10_nota_en_veremos_sin_resaltado_no_sabe_cual_es():
    datos = limpio(notas=("El precio de la pintura está en veremos",))
    assert hallazgos_l10(datos) == [("L10", ADVERTENCIA, PENDIENTE, (NOTAS,), None)]


# --- L10: nota que contradice el total ------------------------------------------------------------


def test_l10_mano_de_obra_como_porcentaje_sin_renglon_es_error():
    # 50 % de 1 570,01 = 785,005 -> 785,01 (redondeo a céntimos, mitad hacia arriba).
    datos = limpio(notas=("La mano de obra será el 50 % del presupuesto total",))
    assert hallazgos_l10(datos) == [("L10", ERROR, NOTA, (NOTAS, f"{P2}:total"), D("785.01"))]
    (h,) = reglas_pdf_simple(leer_pdf_simple(datos, NOMBRE))
    assert (h.valor_observado, h.valor_esperado) == (D("1570.01"), D("2355.02"))


def test_l10_mano_de_obra_con_renglon_propio_no_es_hallazgo():
    # Con un renglón de mano de obra la nota no contradice el total. 6 m2 × 50,00 = 300,00;
    # total 1 445,00 + 125,01 + 300,00 = 1 870,01; cómputos 5 + 1 + 6 = 12, todo en m2.
    datos = pdf_simple(
        (FRISO_C, PINTURA_C, Fila("3", "Mano de obra", "m2", "6")),
        "12",
        (FRISO_P, PINTURA_P, Fila("3", "Mano de obra", "m2", "6", "50.00", "300.00")),
        "1,870.01",
        ("La mano de obra será el 50 % del presupuesto total",),
    )
    assert hallazgos_l10(datos) == []


# --- L10: suma de renglones ≠ TOTAL PRESUPUESTO ---------------------------------------------------


@pytest.mark.parametrize(
    ("total_doc", "impacto"),
    [
        ("1,600.00", D("29.99")),  # 1 600,00 − 1 570,01
        ("1,500.00", D("-70.01")),  # 1 500,00 − 1 570,01: el signo se conserva
        ("1,570.016", D("0.006")),  # frontera + 1
    ],
)
def test_l10_suma_distinta_del_total_impreso_es_error_con_signo(total_doc, impacto):
    assert hallazgos_l10(limpio(total_presupuesto=total_doc)) == [
        ("L10", ERROR, SUMA, (f"{P2}:total",), impacto)
    ]


def test_l10_suma_a_medio_centimo_del_total_no_es_hallazgo():
    assert hallazgos_l10(limpio(total_presupuesto="1,570.015")) == []


def test_l10_sin_linea_total_presupuesto_es_advertencia():
    assert hallazgos_l10(limpio(total_presupuesto=None)) == [
        ("L10", ADVERTENCIA, SUMA, (f"{P2}:total",), None)
    ]


# --- L10: conjunto exacto con varios errores ------------------------------------------------------


def _varios_errores() -> bytes:
    # Cómputos: friso 80 m2, pintura 1 m2, demolición 4 m2 -> suma 85, impreso "85".
    # Presupuesto:
    #   1 friso 90 m2 × 12,50 = 1 125,00 (cuadra)            -> cómputos ≠ presupuesto, +125,00
    #   2 pintura 1 m2 × 125,01 impreso 126,01, resaltado    -> aritmética +1,00; resaltado sin
    #                                                           nota de "en veremos": INFO
    #   suma = 1 125,00 + 126,01 = 1 251,01; impreso 1 300,00 -> suma ≠ total, +48,99
    #   nota: mano de obra 10 % sin renglón                   -> 10 % de 1 300,00 = 130,00
    #   demolición (cómputos) sin pareja                      -> ADVERTENCIA
    return pdf_simple(
        (
            Fila("1", "Friso liso de paredes", "m2", "80"),
            PINTURA_C,
            Fila("3", "Demolición de bloques", "m2", "4"),
        ),
        "85",
        (
            Fila("1", "Friso liso de paredes", "m2", "90", "12.50", "1,125.00"),
            Fila("2", "Pintura de caucho", "m2", "1", "125.01", "126.01", resaltado=True),
        ),
        "1,300.00",
        ("La mano de obra será el 10 % del presupuesto total",),
    )


ESPERADO_VARIOS = conjunto(
    ("L10", ERROR, ARITMETICA, (f"{P2}:item2",), D("1.00")),
    ("L10", ERROR, COMPUTOS, (f"{P1}:item1", f"{P2}:item1"), D("125.00")),
    ("L10", ADVERTENCIA, COMPUTOS, (f"{P1}:item3",), None),
    ("L10", INFO, PENDIENTE, (f"{P2}:item2",), None),
    ("L10", ERROR, NOTA, (NOTAS, f"{P2}:total"), D("130.00")),
    ("L10", ERROR, SUMA, (f"{P2}:total",), D("48.99")),
)


def test_l10_pdf_con_varios_errores_da_el_conjunto_exacto():
    assert hallazgos_l10(_varios_errores()) == ESPERADO_VARIOS


def test_l10_orden_fijo_de_las_reglas():
    """Orden documentado: unidades, filas, cómputos, notas, sumas (determinista)."""
    subtipos = [clave(h)[2] for h in reglas_pdf_simple(leer_pdf_simple(_varios_errores(), NOMBRE))]
    assert subtipos == [ARITMETICA, COMPUTOS, COMPUTOS, PENDIENTE, NOTA, SUMA]


# --- auditar_pdf_simple (PDF simple sin libro, errata 6) ------------------------------------------


def test_auditar_pdf_simple_da_los_hallazgos_l10_todos_informados():
    datos = _varios_errores()
    r = auditar_pdf_simple(datos, NOMBRE)
    assert sorted((clave(h) for h in r.hallazgos), key=repr) == ESPERADO_VARIOS
    assert r.sha256 == hashlib.sha256(datos).hexdigest()
    assert isinstance(r.pdf, PdfSimple)
    assert len(r.hallazgos_tabla) == len(ESPERADO_VARIOS)
    assert {f.accion for f in r.hallazgos_tabla} == {"informado"}
    assert {f.codigo for f in r.hallazgos_tabla} == {"L10"}


def test_auditar_pdf_simple_sin_tablas_no_es_interpretable():
    with pytest.raises(LibroNoInterpretable, match="no tiene una tabla de cómputos"):
        auditar_pdf_simple(paginas_en_blanco(1), NOMBRE)


def test_auditar_pdf_simple_rechaza_lo_que_no_es_pdf():
    with pytest.raises(ArchivoRechazado, match="no es un PDF"):
        auditar_pdf_simple(b"PK\x03\x04 esto es un zip", NOMBRE)


# --- RNF-21: rechazos del PDF ---------------------------------------------------------------------


def test_rnf21_cabecera_pdf_dentro_del_primer_kilobyte():
    base = paginas_en_blanco(1)
    # "%PDF-" en los bytes 1019-1023: dentro de los primeros 1024 -> se abre.
    assert leer_totales_impresos(b"x" * 1019 + base, NOMBRE).paginas == 1
    # Un byte más: "%PDF-" termina en el 1024 y ya no está en el primer kilobyte -> rechazo.
    with pytest.raises(ArchivoRechazado, match="no tiene la cabecera %PDF-"):
        leer_totales_impresos(b"x" * 1020 + base, NOMBRE)


def test_rnf21_pdf_cifrado_se_rechaza():
    cifrado = paginas_en_blanco(1, encrypt="clave-ficticia")
    assert b"/Encrypt" in cifrado
    for leer in (leer_pdf_simple, leer_totales_impresos, _leer_pdf):
        with pytest.raises(ArchivoRechazado, match="cifrado o protegido"):
            leer(cifrado, NOMBRE)


def test_rnf21_pdf_con_javascript_se_rechaza():
    con_js = paginas_en_blanco(1).replace(b"%%EOF", b"% /JavaScript\n%%EOF")
    for leer in (leer_pdf_simple, leer_totales_impresos, _leer_pdf):
        with pytest.raises(ArchivoRechazado, match="contiene JavaScript"):
            leer(con_js, NOMBRE)


def test_rnf21_sesenta_paginas_pasan_y_sesenta_y_una_no():
    assert MAX_PAGINAS_PDF == 60
    assert leer_totales_impresos(paginas_en_blanco(60), NOMBRE).paginas == 60
    with pytest.raises(ArchivoRechazado, match="tiene 61 páginas y el máximo es 60"):
        leer_totales_impresos(paginas_en_blanco(61), NOMBRE)
    with pytest.raises(ArchivoRechazado, match="tiene 61 páginas"):
        leer_pdf_simple(paginas_en_blanco(61), NOMBRE)


def test_rnf21_las_paginas_se_cuentan_aunque_el_count_mienta():
    # /Count dice 1 (mismo largo de bytes) y hay 61 páginas reales: se cuentan las reales.
    datos = paginas_en_blanco(61)
    assert datos.count(b"/Count 61") == 1
    with pytest.raises(ArchivoRechazado, match="tiene 61 páginas"):
        leer_totales_impresos(datos.replace(b"/Count 61", b"/Count 1 "), NOMBRE)
    # /Count dice 99 y hay 10: se rechaza por lo declarado, antes de construir las páginas.
    diez = paginas_en_blanco(10)
    with pytest.raises(ArchivoRechazado, match="tiene 99 páginas"):
        leer_totales_impresos(diez.replace(b"/Count 10", b"/Count 99"), NOMBRE)


def test_rnf21_tamano_maximo_es_25_mib():
    assert MAX_BYTES_PDF == 25 * 1024 * 1024
    demasiado = b"%PDF-1.4\n" + b"\0" * (MAX_BYTES_PDF + 1 - len(b"%PDF-1.4\n"))
    assert len(demasiado) == MAX_BYTES_PDF + 1
    with pytest.raises(ArchivoRechazado, match="supera el máximo de 25 MiB"):
        leer_pdf_simple(demasiado, NOMBRE)


def test_rnf21_frontera_de_tamano(monkeypatch):
    # Se baja el tope al largo exacto de un PDF válido: ese largo pasa; un byte menos de tope, no.
    datos = paginas_en_blanco(1)
    monkeypatch.setattr(modulo_pdf, "MAX_BYTES_PDF", len(datos))
    assert leer_totales_impresos(datos, NOMBRE).paginas == 1
    monkeypatch.setattr(modulo_pdf, "MAX_BYTES_PDF", len(datos) - 1)
    with pytest.raises(ArchivoRechazado, match="supera el máximo"):
        leer_totales_impresos(datos, NOMBRE)


def test_rnf21_pdf_danado_da_mensaje_fijo_sin_texto_tecnico():
    danado = b"%PDF-1.4\n1 0 obj << /Type /Catalog >>\nbasura sin xref"
    with pytest.raises(ArchivoRechazado) as exc:
        leer_pdf_simple(danado, NOMBRE)
    assert str(exc.value) == (
        f"El PDF «{NOMBRE}» no se pudo leer: está dañado, protegido o no es un PDF de "
        "presupuesto. Imprímalo de nuevo a PDF desde el programa original."
    )


# --- L11: totales impresos contra el libro --------------------------------------------------------


@pytest.fixture(scope="module")
def libro():
    return leer_libro(libro_limpio().datos, "libro_sintetico.xlsx")


ORIGEN_LIBRO = {
    "SUBSINIVA": "PRESUPUESTO!Q10",
    "IVATOT": "PRESUPUESTO!Q11",
    "TOTALGEN": "PRESUPUESTO!Q12",
}

IMPRESO = ("", "$4,358.21", "$697.31", "$5,055.52")


def test_l11_lee_el_bloque_de_totales_impreso():
    t = leer_totales_impresos(pdf_impreso([IMPRESO]), NOMBRE)
    assert (t.subtotal, t.iva, t.total) == (D("4358.21"), D("697.31"), D("5055.52"))
    assert (t.paginas, t.pagina, t.bloques, t.opcion, t.nota) == (1, 1, 1, "", "")


def test_l11_impreso_que_coincide_con_el_libro_no_da_hallazgos(libro):
    # |4 358,21 − 4 358,20825| = 0,00175; |697,31 − 697,31332| = 0,00332;
    # |5 055,52 − 5 055,52157| = 0,00157: todas < 0,005.
    assert libro.totales == {
        "SUBSINIVA": MEMORIA["SUBSINIVA"],
        "IVATOT": MEMORIA["IVATOT"],
        "TOTALGEN": MEMORIA["TOTALGEN"],
    }
    totales = leer_totales_impresos(pdf_impreso([IMPRESO]), NOMBRE)
    assert cotejar_con_libro(totales, libro) == []


@pytest.mark.parametrize(
    ("subtotal", "esperado"),
    [
        ("$4,358.21325", None),  # 4 358,21325 − 4 358,20825 = 0,005: no es hallazgo
        ("$4,358.21425", D("0.006")),  # 0,006 > 0,005: ERROR, impacto = PDF − libro
        ("$4,358.20225", D("-0.006")),  # por debajo, con signo
    ],
)
def test_l11_frontera_del_subtotal(libro, subtotal, esperado):
    totales = leer_totales_impresos(pdf_impreso([("", subtotal, "$697.31", "$5,055.52")]), NOMBRE)
    hallazgos = cotejar_con_libro(totales, libro)
    if esperado is None:
        assert hallazgos == []
        return
    (h,) = hallazgos
    assert (h.regla, h.severidad, h.impacto) == ("L11", ERROR, esperado)
    assert h.valor_observado - h.valor_esperado == esperado
    assert h.valor_esperado == MEMORIA["SUBSINIVA"]
    assert h.origen_ids == (f"PDF:{NOMBRE}:p1", ORIGEN_LIBRO["SUBSINIVA"])
    assert h.descripcion.startswith("subtotal sin IVA: ")


def test_l11_con_dos_bloques_se_coteja_el_ultimo(libro):
    # OPCIÓN B (otra cifra) y OPCIÓN DEFINITIVA (la del libro): se toma la definitiva -> nada.
    datos = pdf_impreso(
        [
            ("OPCIÓN B", "$3,000.00", "$480.00", "$3,480.00"),
            ("OPCIÓN DEFINITIVA", *IMPRESO[1:]),
        ]
    )
    t = leer_totales_impresos(datos, NOMBRE)
    assert (t.subtotal, t.pagina, t.bloques, t.opcion) == (D("4358.21"), 2, 2, "OPCIÓN DEFINITIVA")
    assert "2 bloques de totales distintos" in t.nota
    assert cotejar_con_libro(t, libro) == []


def test_l11_con_dos_bloques_el_ultimo_discordante_da_tres_errores(libro):
    # Al revés: la B coincide con el libro y la definitiva no -> L11 ERROR en las tres cifras.
    # 3 000,00 − 4 358,20825 = −1 358,20825; 480,00 − 697,31332 = −217,31332;
    # 3 480,00 − 5 055,52157 = −1 575,52157.
    datos = pdf_impreso(
        [
            ("OPCIÓN B", *IMPRESO[1:]),
            ("OPCIÓN DEFINITIVA", "$3,000.00", "$480.00", "$3,480.00"),
        ]
    )
    hallazgos = cotejar_con_libro(leer_totales_impresos(datos, NOMBRE), libro)
    assert [(h.regla, h.severidad, h.impacto, h.origen_ids) for h in hallazgos] == [
        ("L11", ERROR, D("-1358.20825"), (f"PDF:{NOMBRE}:p2", ORIGEN_LIBRO["SUBSINIVA"])),
        ("L11", ERROR, D("-217.31332"), (f"PDF:{NOMBRE}:p2", ORIGEN_LIBRO["IVATOT"])),
        ("L11", ERROR, D("-1575.52157"), (f"PDF:{NOMBRE}:p2", ORIGEN_LIBRO["TOTALGEN"])),
    ]
    assert all("«OPCIÓN DEFINITIVA»" in h.descripcion for h in hallazgos)


def test_l11_cifra_ausente_en_el_pdf_es_advertencia(libro):
    totales = leer_totales_impresos(pdf_impreso([("", "$4,358.21", None, "$5,055.52")]), NOMBRE)
    assert totales.iva is None
    (h,) = cotejar_con_libro(totales, libro)
    assert (h.regla, h.severidad, h.impacto) == ("L11", ADVERTENCIA, None)
    assert (h.valor_observado, h.valor_esperado) == (None, MEMORIA["IVATOT"])
    assert h.descripcion.startswith("IVA: el PDF no trae la cifra")


def test_l11_cotejo_con_totales_construidos_a_mano(libro):
    # Mismo cotejo sin PDF: el impacto es PDF − libro exactamente.
    t = TotalesImpresos(NOMBRE, D("4358.20825"), D("697.31332"), D("5055.53157"), 1, pagina=1)
    (h,) = cotejar_con_libro(t, libro)
    assert (h.regla, h.severidad, h.impacto) == ("L11", ERROR, D("0.01000"))
    assert h.descripcion.startswith("total con IVA: ")


# --- Errata 6: el PDF que llega con el libro decide L10 o L11 -------------------------------------


def test_leer_pdf_distingue_impreso_simple_y_vacio():
    assert isinstance(_leer_pdf(pdf_impreso([IMPRESO]), NOMBRE), TotalesImpresos)
    assert isinstance(_leer_pdf(limpio(), NOMBRE), PdfSimple)
    # Sin bloque ni tablas: se trata como impreso (L11 dirá que faltan las cifras).
    vacio = _leer_pdf(paginas_en_blanco(1), NOMBRE)
    assert isinstance(vacio, TotalesImpresos)
    assert (vacio.subtotal, vacio.iva, vacio.total, vacio.bloques) == (None, None, None, 0)


def _codigos(reglas) -> list[str]:
    return [r[0] for r in reglas]


FECHA = date(2026, 8, 1)


def test_procesar_libro_con_el_impreso_evalua_l11_y_no_l10():
    c = libro_limpio()
    r = procesar_libro(c.datos, "libro.xlsx", pdf=pdf_impreso([IMPRESO]), fecha_devolucion=FECHA)
    assert "L11" in _codigos(r.informe.reglas_evaluadas)
    assert "L10" not in _codigos(r.informe.reglas_evaluadas)
    assert [r_ for r_ in r.reglas_no_evaluadas if r_[0] in ("L10", "L11")] == [
        (
            "L10",
            "Documento sin modelo (PDF simple)",
            "el PDF recibido es el impreso del libro: se cotejó con L11",
        )
    ]
    # El impreso coincide con el libro: el conjunto es el del libro limpio, {R2 INFO, R7 INFO}.
    assert sorted((h.regla, h.severidad) for h in r.informe.hallazgos) == [
        ("R2", INFO),
        ("R7", INFO),
    ]
    assert r.pdf_simple is None
    assert r.pdf_totales is not None and r.pdf_totales.subtotal == D("4358.21")


def test_procesar_libro_con_impreso_discordante_informa_l11():
    c = libro_limpio()
    impreso = pdf_impreso([("", "$4,358.21425", "$697.31", "$5,055.52")])
    r = procesar_libro(c.datos, "libro.xlsx", pdf=impreso, fecha_devolucion=FECHA)
    l11 = [h for h in r.informe.hallazgos if h.regla == "L11"]
    assert [(h.severidad, h.impacto) for h in l11] == [(ERROR, D("0.006"))]
    assert {f.accion for f in r.hallazgos_tabla if f.codigo == "L11"} == {"informado"}


def test_procesar_libro_con_pdf_simple_evalua_l10_y_no_l11():
    c = libro_limpio()
    datos_pdf = _varios_errores()  # reportlab no es determinista: un solo juego de bytes
    r = procesar_libro(c.datos, "libro.xlsx", pdf=datos_pdf, fecha_devolucion=FECHA)
    assert "L10" in _codigos(r.informe.reglas_evaluadas)
    assert "L11" not in _codigos(r.informe.reglas_evaluadas)
    assert [r_ for r_ in r.reglas_no_evaluadas if r_[0] in ("L10", "L11")] == [
        (
            "L11",
            "Libro ↔ PDF entregado",
            "el PDF recibido no trae el bloque de totales del libro impreso: es un PDF simple y "
            "se revisó con L10",
        )
    ]
    l10 = sorted(
        (clave(h) for h in r.informe.hallazgos if h.regla == "L10"),
        key=repr,
    )
    # El nombre por omisión del PDF que llega con el libro es "entregado.pdf".
    assert l10 == [
        (a, b, c_, tuple(o.replace(NOMBRE, "entregado.pdf") for o in orig), imp)
        for a, b, c_, orig, imp in ESPERADO_VARIOS
    ]
    assert sorted(
        (h.regla, h.severidad) for h in r.informe.hallazgos if h.regla not in ("L10",)
    ) == [("R2", INFO), ("R7", INFO)]
    assert r.pdf_totales is None
    assert isinstance(r.pdf_simple, PdfSimple)
    assert r.metadatos["sha256_pdf"] == hashlib.sha256(datos_pdf).hexdigest()


def test_procesar_libro_con_pdf_sin_cifras_da_tres_advertencias_l11():
    c = libro_limpio()
    r = procesar_libro(c.datos, "libro.xlsx", pdf=paginas_en_blanco(1), fecha_devolucion=FECHA)
    l11 = [(h.severidad, h.impacto) for h in r.informe.hallazgos if h.regla == "L11"]
    assert l11 == [(ADVERTENCIA, None)] * 3


def test_procesar_libro_rechaza_un_pdf_cifrado():
    c = libro_limpio()
    with pytest.raises(ArchivoRechazado, match="cifrado o protegido"):
        procesar_libro(
            c.datos,
            "libro.xlsx",
            pdf=paginas_en_blanco(1, encrypt="clave-ficticia"),
            fecha_devolucion=FECHA,
        )
