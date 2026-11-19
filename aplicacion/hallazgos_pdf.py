"""El informe de hallazgos de la auditoría de un libro en PDF (decisión P2 de Eugenio, 2026-11-19).

Dos pasos, como `aplicacion.presupuesto_pdf`:

1. Quien llama (la ruta `POST /v1/libros/auditoria/pdf`) arma un `InformeDeHallazgos` con solo
   textos: el libro, las fechas, el veredicto, el conteo por severidad, los totales del libro frente
   a los de Sílice y una fila por hallazgo. Las cifras salen del servidor, del mismo cálculo que
   la pantalla; aquí solo se escriben con coma decimal y punto de miles (`dinero`).
2. `pdf_de_hallazgos` lo dibuja con reportlab (extra `informes`): carta vertical, la letra Vera
   incrustada (tildes, «m³»), el encabezado de la tabla repetido en cada página, «Página n de N»
   y el libro en el pie. Todo texto de la persona se escapa: un «<b>» en una descripción se ve
   tal cual.

No escribe nada y no guarda ni el libro ni el PDF (RNF-28). Sin FastAPI (RM-1).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from aplicacion.cifras import texto_de_cifra
from aplicacion.presupuesto_pdf import (
    _LARGO_MAXIMO,
    _LETRA,
    _NEGRITA,
    _NO_SEGURO,
    _limpio,
    _registrar_letras,
)

TITULO = "Hallazgos de la auditoría"
SIN_HALLAZGOS = "El libro no tiene hallazgos."
LIBRO_POR_OMISION = "libro"
_EXTENSION = ".xlsx"


@dataclass(frozen=True, slots=True)
class FilaDeHallazgo:
    """Un hallazgo ya escrito: `severidad` con su nombre («Error»), `impacto` vacío si no tiene."""

    codigo: str
    severidad: str
    celda: str
    descripcion: str
    impacto: str
    accion: str


@dataclass(frozen=True, slots=True)
class LineaDeTotal:
    concepto: str
    libro: str
    silice: str


@dataclass(frozen=True, slots=True)
class InformeDeHallazgos:
    libro: str
    fecha_libro: str
    fecha_devolucion: str
    emitido: str
    veredicto: str
    conteo: tuple[str, ...]
    totales: tuple[LineaDeTotal, ...]
    hallazgos: tuple[FilaDeHallazgo, ...]


def dinero(valor: Decimal) -> str:
    """Un monto a dos decimales al alza, con coma decimal y punto de miles; nunca «-0,00»."""
    return texto_de_cifra(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def nombre_del_pdf_de_hallazgos(nombre_libro: str) -> str:
    """`hallazgos_{libro}.pdf`: el nombre del libro sin «.xlsx», con cada carácter fuera de
    A-Z a-z 0-9 . _ - cambiado por «_» y acotado (el recorte va antes)."""
    base = nombre_libro
    if base.lower().endswith(_EXTENSION):
        base = base[: -len(_EXTENSION)]
    seguro = _NO_SEGURO.sub("_", base[:_LARGO_MAXIMO]) or LIBRO_POR_OMISION
    return f"hallazgos_{seguro}.pdf"


def pdf_de_hallazgos(informe: InformeDeHallazgos) -> bytes:
    """El PDF del informe, en carta vertical."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    _registrar_letras()
    normal = ParagraphStyle("normal", fontName=_LETRA, fontSize=8, leading=10)
    celda = ParagraphStyle("celda", parent=normal, fontSize=7.5, leading=9, embeddedHyphenation=1)
    negrita = ParagraphStyle("negrita", parent=celda, fontName=_NEGRITA)
    derecha = ParagraphStyle("derecha", parent=celda, alignment=TA_RIGHT)
    titulo_derecha = ParagraphStyle("titulo_derecha", parent=negrita, alignment=TA_RIGHT)
    titulo = ParagraphStyle("titulo", parent=normal, fontName=_NEGRITA, fontSize=15, leading=19)
    subtitulo = ParagraphStyle("sub", parent=normal, fontName=_NEGRITA, fontSize=11, leading=14)

    def p(texto: str, estilo: ParagraphStyle = celda) -> Paragraph:
        return Paragraph(escape(_limpio(texto)), estilo)

    base = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#a8a8a8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]

    historia: list = [
        p(TITULO, titulo),
        p(informe.libro, subtitulo),
        Spacer(1, 4),
        p(f"Fecha del libro: {informe.fecha_libro}", normal),
        p(f"Fecha de devolución: {informe.fecha_devolucion}", normal),
        p(f"Emitido el {informe.emitido}", normal),
        p(f"Resultado: {informe.veredicto}", ParagraphStyle("v", parent=normal, fontName=_NEGRITA)),
        p(" · ".join(informe.conteo), normal),
        Spacer(1, 8),
    ]

    if informe.totales:
        filas = [
            [
                p("Total", negrita),
                p("Según el libro", titulo_derecha),
                p("Según Sílice", titulo_derecha),
            ]
        ]
        filas += [
            [p(t.concepto), p(t.libro, derecha), p(t.silice, derecha)] for t in informe.totales
        ]
        totales = Table(filas, colWidths=[6 * cm, 3.6 * cm, 3.6 * cm], hAlign="LEFT")
        totales.setStyle(TableStyle(base))
        historia += [totales, Spacer(1, 10)]

    anchos = [1.3 * cm, 2.1 * cm, 3.3 * cm, 7.0 * cm, 2.2 * cm, 2.4 * cm]
    filas = [
        [
            p("Regla", negrita),
            p("Severidad", negrita),
            p("Celda", negrita),
            p("Descripción", negrita),
            p("Impacto", titulo_derecha),
            p("Acción", negrita),
        ]
    ]
    if not informe.hallazgos:
        filas.append([p(SIN_HALLAZGOS), "", "", "", "", ""])
    filas += [
        [
            p(h.codigo),
            p(h.severidad),
            p(h.celda),
            p(h.descripcion),
            p(h.impacto, derecha),
            p(h.accion),
        ]
        for h in informe.hallazgos
    ]
    tabla = Table(filas, colWidths=anchos, repeatRows=1)
    estilo = list(base)
    if not informe.hallazgos:
        estilo.append(("SPAN", (0, 1), (-1, 1)))
    tabla.setStyle(TableStyle(estilo))
    historia.append(tabla)

    pie = _limpio(f"Sílice · {informe.libro} · hallazgos de la auditoría")

    class _Numerado(Canvas):
        """«Página n de N»: las páginas se guardan y se numeran al final, cuando ya se sabe N."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._paginas: list[dict] = []

        def showPage(self):  # noqa: N802 (la API de reportlab)
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._paginas)
            for numero, estado in enumerate(self._paginas, start=1):
                self.__dict__.update(estado)
                self.setFont(_LETRA, 7)
                self.setFillColor(colors.HexColor("#525252"))
                self.drawString(1.5 * cm, 1 * cm, pie[:150])
                self.drawRightString(letter[0] - 1.5 * cm, 1 * cm, f"Página {numero} de {total}")
                super().showPage()
            super().save()

    salida = BytesIO()
    SimpleDocTemplate(
        salida,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        title=_limpio(f"{TITULO} · {informe.libro}"),
        author="Sílice",
        creator="Sílice",
    ).build(historia, canvasmaker=_Numerado)
    return salida.getvalue()


__all__ = (
    "InformeDeHallazgos",
    "FilaDeHallazgo",
    "LineaDeTotal",
    "dinero",
    "nombre_del_pdf_de_hallazgos",
    "pdf_de_hallazgos",
)
