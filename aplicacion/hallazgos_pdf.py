"""El informe de hallazgos de la auditoría de un libro en PDF (botón «Descargar PDF» del visor).

P2 del Word del 2026-11-19: la eligió Claude con Eugenio ausente (acta DS-77); Eugenio la
conservó ese día y pidió el nombre corto del botón con una línea que diga qué baja.

Dos pasos, como `aplicacion.presupuesto_pdf`:

1. Quien llama (la ruta `POST /v1/libros/auditoria/pdf`) arma un `InformeDeHallazgos` con solo
   textos: el libro, las fechas, el veredicto, el conteo por severidad, los totales del libro frente
   a los de Sílice y una fila por hallazgo. Las cifras salen del servidor, del mismo cálculo que
   la pantalla; aquí solo se escriben con coma decimal y punto de miles (`dinero`).
2. `pdf_de_hallazgos` lo dibuja con reportlab (extra `informes`): carta vertical, la letra Vera
   incrustada (tildes, «m³»), el encabezado de la tabla repetido en cada página, «Página n de N»
   y el libro en el pie. Todo texto de la persona se escapa: un «<b>» en una descripción se ve
   tal cual.

Un libro roto u hostil no tumba el informe: cada texto largo se corta con «…», una fila más alta
que la página se parte entre páginas y, pasadas `MAX_FILAS` filas, el resto se cuenta en una línea.

No escribe nada y no guarda ni el libro ni el PDF (RNF-28). Sin FastAPI (RM-1).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.sax.saxutils import escape

from aplicacion.cifras import texto_de_cifra
from aplicacion.presupuesto_pdf import (
    _LARGO_MAXIMO,
    _LETRA,
    _NEGRITA,
    _NO_SEGURO,
    _SEVERIDADES,
    _limpio,
    _registrar_letras,
)
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

TITULO = "Hallazgos de la auditoría"
SIN_HALLAZGOS = "El libro no tiene hallazgos."
LIBRO_POR_OMISION = "libro"
_EXTENSION = ".xlsx"
#: Lo más largo que se escribe la descripción, la acción o la celda de un hallazgo (un libro roto
#: u hostil puede traer miles de caracteres en una celda): lo demás se corta con «…».
TOPE_DE_TEXTO = 1_500
#: Lo más largo que se escribe el nombre del libro en el subtítulo y en los metadatos.
TOPE_DEL_LIBRO = 150
#: Cuántos hallazgos se dibujan; el resto se cuenta en una fila final.
MAX_FILAS = 2_000
_HUELLA = "Huella del libro (SHA-256)"
_TAMANO_DEL_PIE = 7


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
    #: Los primeros caracteres del SHA-256 del libro: ata el informe al archivo auditado.
    huella: str = ""


#: La severidad como la escribe la interfaz (`severidad/severidad.ts`), de la más a la menos grave.
_NOMBRES = {
    "CRITICO": "Crítico",
    "ERROR": "Error",
    "ADVERTENCIA": "Advertencia",
    "INFO": "Información",
}


def severidad_escrita(severidad: str) -> str:
    """«ERROR» -> «Error»; una severidad desconocida se muestra tal cual."""
    return _NOMBRES.get(severidad, severidad)


def conteo_por_severidad(severidades: Iterable[str]) -> tuple[str, ...]:
    """«4 errores», «2 avisos informativos»: de la más a la menos grave y solo las que hay; sin
    ninguna, «Sin hallazgos». Una severidad que el informe no conoce se cuenta al final."""
    cuenta = Counter(severidades)
    partes = []
    for clave, (singular, plural) in _SEVERIDADES.items():
        if cuenta[clave]:
            partes.append(f"{cuenta[clave]} {singular if cuenta[clave] == 1 else plural}")
    partes += [f"{cuenta[c]} con severidad «{c}»" for c in sorted(cuenta) if c not in _SEVERIDADES]
    return tuple(partes) or ("Sin hallazgos",)


def dinero(valor: Decimal) -> str:
    """Un monto como lo presenta la pantalla (dos decimales al alza, `core.verification.texto`:
    decisión de Eugenio del 2026-11-17), con coma decimal y punto de miles y nunca «-0,00». Si no
    cabe en la precisión decimal al redondear (más de ~26 cifras enteras), el exacto."""
    try:
        redondeado = formatear_decimal(valor, DECIMALES_PRESENTACION)
    except InvalidOperation:
        redondeado = formatear_decimal(valor)
    return texto_de_cifra(Decimal(redondeado))


def nombre_del_pdf_de_hallazgos(nombre_libro: str) -> str:
    """`hallazgos_{libro}.pdf`: el nombre del libro sin «.xlsx», con cada carácter fuera de
    A-Z a-z 0-9 . _ - cambiado por «_» y acotado (el recorte va antes)."""
    base = nombre_libro
    if base.lower().endswith(_EXTENSION):
        base = base[: -len(_EXTENSION)]
    seguro = _NO_SEGURO.sub("_", base[:_LARGO_MAXIMO]) or LIBRO_POR_OMISION
    return f"hallazgos_{seguro}.pdf"


def _acotar(texto: str, tope: int) -> str:
    """El texto, o sus primeros `tope - 1` caracteres y «…» si pasa de `tope`."""
    return texto if len(texto) <= tope else texto[: tope - 1] + "…"


def _mas_filas(n: int) -> str:
    return (
        f"y {n} hallazgos más; véalos en Sílice" if n != 1 else "y 1 hallazgo más; véalo en Sílice"
    )


def _pie(libro: str, libre: float) -> str:
    """«Sílice · {libro} · hallazgos de la auditoría» en `libre` puntos como máximo: si no cabe,
    se recorta solo el nombre del libro (con «…») y se conserva el resto."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    prefijo, sufijo = "Sílice · ", " · hallazgos de la auditoría"

    def ancho(texto: str) -> float:
        return stringWidth(texto, _LETRA, _TAMANO_DEL_PIE)

    nombre = _limpio(libro)
    if ancho(prefijo + nombre + sufijo) <= libre:
        return prefijo + nombre + sufijo
    cabe = libre - ancho(prefijo + "…" + sufijo)
    desde, hasta = 0, len(nombre)
    while desde < hasta:
        medio = (desde + hasta + 1) // 2
        if ancho(nombre[:medio]) <= cabe:
            desde = medio
        else:
            hasta = medio - 1
    return prefijo + nombre[:desde] + "…" + sufijo


def pdf_de_hallazgos(informe: InformeDeHallazgos) -> bytes:
    """El PDF del informe, en carta vertical."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    _registrar_letras()
    normal = ParagraphStyle("normal", fontName=_LETRA, fontSize=8, leading=10)
    celda = ParagraphStyle("celda", parent=normal, fontSize=7.5, leading=9, embeddedHyphenation=1)
    negrita = ParagraphStyle("negrita", parent=celda, fontName=_NEGRITA)
    # una cifra no se parte en su signo «-» (embeddedHyphenation=0): sale entera en una línea
    derecha = ParagraphStyle("derecha", parent=celda, alignment=TA_RIGHT, embeddedHyphenation=0)
    titulo_derecha = ParagraphStyle("titulo_derecha", parent=negrita, alignment=TA_RIGHT)
    titulo = ParagraphStyle("titulo", parent=normal, fontName=_NEGRITA, fontSize=15, leading=19)
    subtitulo = ParagraphStyle("sub", parent=normal, fontName=_NEGRITA, fontSize=11, leading=14)

    def p(texto: str, estilo: ParagraphStyle = celda) -> Paragraph:
        return Paragraph(escape(_limpio(texto)), estilo)

    base = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#a8a8a8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]

    libro = _acotar(informe.libro, TOPE_DEL_LIBRO)
    historia: list = [
        p(TITULO, titulo),
        p(libro, subtitulo),
        Spacer(1, 4),
        p(f"Fecha del libro: {informe.fecha_libro}", normal),
        p(f"Fecha de devolución: {informe.fecha_devolucion}", normal),
        p(f"Emitido el {informe.emitido}", normal),
        p(f"Resultado: {informe.veredicto}", ParagraphStyle("v", parent=normal, fontName=_NEGRITA)),
        p(" · ".join(informe.conteo), normal),
        *([p(f"{_HUELLA}: {informe.huella}", normal)] if informe.huella else []),
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

    anchos = [1.5 * cm, 2.0 * cm, 3.1 * cm, 6.5 * cm, 3.0 * cm, 2.4 * cm]
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
    mostrados = informe.hallazgos[:MAX_FILAS]
    faltan = len(informe.hallazgos) - len(mostrados)
    if not informe.hallazgos:
        filas.append([p(SIN_HALLAZGOS), "", "", "", "", ""])
    filas += [
        [
            p(_acotar(h.codigo, TOPE_DEL_LIBRO)),
            p(h.severidad),
            p(_acotar(h.celda, TOPE_DE_TEXTO)),
            p(_acotar(h.descripcion, TOPE_DE_TEXTO)),
            p(h.impacto, derecha),
            p(_acotar(h.accion, TOPE_DE_TEXTO)),
        ]
        for h in mostrados
    ]
    if faltan:
        filas.append([p(_mas_filas(faltan), negrita), "", "", "", "", ""])
    # splitInRow: una fila aún más alta que la página se parte en vez de tumbar el documento
    tabla = Table(filas, colWidths=anchos, repeatRows=1, splitInRow=1)
    estilo = list(base)
    if not informe.hallazgos or faltan:
        ultima = len(filas) - 1
        estilo.append(("SPAN", (0, ultima), (-1, ultima)))
    tabla.setStyle(TableStyle(estilo))
    historia.append(tabla)

    # el pie deja libre el sitio de «Página n de N» (hasta cuatro cifras en cada número)
    reservado = stringWidth("Página 9999 de 9999", _LETRA, _TAMANO_DEL_PIE)
    pie = _pie(informe.libro, letter[0] - 3 * cm - reservado - 12)

    class _Numerado(Canvas):
        """«Página n de N»: las páginas se guardan y se numeran al final, cuando ya se sabe N."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._paginas: list[dict] = []

        def showPage(self):  # noqa: N802 (la API de reportlab)
            # la foto del estado no lleva la lista de fotos: sería cuadrático en páginas
            self._paginas.append({k: v for k, v in self.__dict__.items() if k != "_paginas"})
            self._startPage()

        def save(self):
            total = len(self._paginas)
            for numero, estado in enumerate(self._paginas, start=1):
                self.__dict__.update(estado)
                self.setFont(_LETRA, _TAMANO_DEL_PIE)
                self.setFillColor(colors.HexColor("#525252"))
                self.drawString(1.5 * cm, 1 * cm, pie)
                self.drawRightString(letter[0] - 1.5 * cm, 1 * cm, f"Página {numero} de {total}")
                super().showPage()
            super().save()
            self._paginas.clear()

    salida = BytesIO()
    SimpleDocTemplate(
        salida,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        title=_limpio(f"{TITULO} · {libro}"),
        author="Sílice",
        creator="Sílice",
    ).build(historia, canvasmaker=_Numerado)
    return salida.getvalue()


__all__ = (
    "InformeDeHallazgos",
    "FilaDeHallazgo",
    "LineaDeTotal",
    "conteo_por_severidad",
    "dinero",
    "nombre_del_pdf_de_hallazgos",
    "pdf_de_hallazgos",
    "severidad_escrita",
)
