"""El presupuesto de la Hoja en PDF y el APU de cada partida (RF-213; ola 2, línea 4, 2026-11-13).

Dos pasos, cada uno con su prueba (`tests/unit/test_presupuesto_pdf.py`):

1. `documento_de_la_hoja` arma un `DocumentoPdf` (solo textos) con las mismas vistas que pinta la
   Hoja (`aplicacion.hoja_vista`): las cifras salen del servidor, del cálculo del borrador vivo, y
   aquí solo se escriben con coma decimal y punto de miles (`aplicacion.cifras.texto_de_cifra`);
   el IVA es el de la pestaña (`aplicacion.impuestos.con_iva` sobre el total exacto).
2. `pdf_en_bytes` lo dibuja con reportlab (extra `informes`, ya en la capa básica del instalador):
   tamaño carta, la letra Vera que trae reportlab incrustada (tildes, «m³», «≤»), el encabezado de
   la tabla repetido en cada página, «Página n de N» y la obra en el pie, y un APU por página.

**Punto de extensión del agrupado** (por frente, de otra línea): `documento_de_la_hoja` recibe un
`Agrupador` que reparte las filas de la vista en grupos con título; el servidor suma el subtotal
de cada grupo con los totales exactos de sus filas. Por omisión, `sin_agrupar`: un solo grupo sin
título ni subtotal. El dibujo ya sabe pintar varios grupos (título y subtotal de cada uno).

No escribe nada: ni la base, ni el borrador (`rev` no cambia). Sin FastAPI (RM-1).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from aplicacion import hoja_vista
from aplicacion.cifras import CifraInvalida, cifra_escrita, texto_de_cifra
from aplicacion.hoja_borradores import BorradorVivo
from aplicacion.hoja_vista import FilaDePresupuesto, Monto
from aplicacion.impuestos import ALICUOTA_IVA, con_iva
from aplicacion.plural import plural

TITULO_PRESUPUESTO = "Presupuesto"
TITULO_APU = "Análisis de precio unitario"
SIN_VERSION = "Borrador sin guardar"
SIN_RENGLONES = "El presupuesto no tiene renglones todavía."
SIN_LINEAS = "Sin líneas"
PENDIENTE = "pendiente"
POR_UNIDAD = "Por unidad de partida"
#: Las columnas del APU que son cifras exactas (se escriben sin redondear) y las que son montos.
_EXACTAS = frozenset({"cantidad", "depreciacion"})
_MONTOS = frozenset({"precio", "sueldo"})
_SEVERIDADES = {
    "CRITICO": ("crítico", "críticos"),
    "ERROR": ("error", "errores"),
    "ADVERTENCIA": ("advertencia", "advertencias"),
    "INFO": ("aviso informativo", "avisos informativos"),
}
_NO_SEGURO = re.compile(r"[^A-Za-z0-9._-]")
_LARGO_MAXIMO = 100
#: Lo que una letra no puede dibujar ni el lector de marcas de reportlab admite: los controles C0
#: (salvo tabulador y salto de línea) y los sustitutos sueltos. Pasan a U+FFFD, como en el Excel.
_PROHIBIDOS = re.compile(
    "[" + chr(0) + "-" + chr(8) + chr(11) + "-" + chr(31) + chr(0xD800) + "-" + chr(0xDFFF) + "]"
)


class PartidaSinApu(LookupError):  # noqa: N818 (como TasaNoDisponible del núcleo)
    """La partida pedida no tiene un APU valorado en el borrador."""


@dataclass(frozen=True, slots=True)
class Encabezado:
    titulo: str
    obra: str
    version: str
    fecha: str
    emitido: str
    moneda: str
    notas: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Renglon:
    numero: str
    partida: str
    descripcion: str
    unidad: str
    cantidad: str
    precio_unitario: str
    total: str


@dataclass(frozen=True, slots=True)
class Grupo:
    """Un grupo de renglones: sin título (el único grupo de `sin_agrupar`) no lleva subtotal."""

    titulo: str
    renglones: tuple[Renglon, ...]
    subtotal: str | None


@dataclass(frozen=True, slots=True)
class LineaDeCierre:
    concepto: str
    monto: str


@dataclass(frozen=True, slots=True)
class TablaDeApu:
    rotulo: str
    columnas: tuple[str, ...]
    filas: tuple[tuple[str, ...], ...]
    subtotal: str


@dataclass(frozen=True, slots=True)
class ApuDelPdf:
    codigo: str
    descripcion: str
    unidad: str
    rendimiento: str
    parametros: str
    tablas: tuple[TablaDeApu, ...]
    cierre: tuple[LineaDeCierre, ...]


@dataclass(frozen=True, slots=True)
class DocumentoPdf:
    encabezado: Encabezado
    grupos: tuple[Grupo, ...]
    totales: tuple[LineaDeCierre, ...]
    notas_finales: tuple[str, ...]
    apus: tuple[ApuDelPdf, ...]


#: Reparte las filas de la vista del presupuesto en grupos (título, filas), en el orden en que se
#: imprimen. La numeración de los renglones sigue de un grupo al siguiente.
Agrupador = Callable[
    [Sequence[FilaDePresupuesto]], Sequence[tuple[str, Sequence[FilaDePresupuesto]]]
]


def sin_agrupar(filas: Sequence[FilaDePresupuesto]) -> list[tuple[str, list[FilaDePresupuesto]]]:
    """Un solo grupo, sin título: el presupuesto como lo muestra la Hoja hoy."""
    return [("", list(filas))]


# --- las cifras -----------------------------------------------------------------------------------


def _dinero(valor: Decimal) -> str:
    return texto_de_cifra(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _de_monto(monto: Monto | None) -> str:
    return PENDIENTE if monto is None else texto_de_cifra(Decimal(monto.texto))


def _porcentaje(fraccion: Decimal) -> str:
    return texto_de_cifra((fraccion * 100).normalize())


def _celda(clave: str, texto: str) -> str:
    """Una celda del APU: las cifras exactas tal cual; los montos a dos decimales. Las celdas ya
    vienen en es-VE (`composicion.filas_desde_composicion`): se leen con `cifra_escrita`, no con
    `Decimal`, que leería «1.000» como uno."""
    if not texto or (clave not in _EXACTAS and clave not in _MONTOS):
        return texto
    try:
        valor = cifra_escrita(texto)
    except CifraInvalida:
        return texto
    return _dinero(valor) if clave in _MONTOS else texto_de_cifra(valor)


# --- el documento --------------------------------------------------------------------------------


def _version(vivo: BorradorVivo) -> str:
    return SIN_VERSION if vivo.version is None else f"Versión {vivo.version}"


def _auditoria(resumen: hoja_vista.ResumenHoja) -> str:
    if not resumen.hallazgos:
        return "Auditoría de Sílice: sin hallazgos."
    partes = [
        plural(h.total, *_SEVERIDADES.get(h.severidad, (h.severidad.lower(),) * 2))
        for h in resumen.hallazgos
    ]
    lista = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
    return f"Auditoría de Sílice: {lista}."


def _notas(vivo: BorradorVivo, resumen, pendientes: int) -> tuple[str, ...]:
    notas = []
    if vivo.version is not None and resumen.cambios:
        notas.append(
            f"Versión {vivo.version} con {plural(resumen.cambios, 'cambio', 'cambios')} "
            "sin guardar."
        )
    if pendientes:
        notas.append(
            f"{plural(pendientes, 'partida', 'partidas')} sin APU en el catálogo: "
            "no suman al total."
        )
    notas.append(_auditoria(resumen))
    return tuple(notas)


def _grupos(filas: Sequence[FilaDePresupuesto], agrupar: Agrupador) -> tuple[Grupo, ...]:
    repartidas = list(agrupar(filas))
    solo = len(repartidas) == 1 and not repartidas[0][0]
    numero, grupos = 0, []
    for titulo, del_grupo in repartidas:
        renglones = []
        for fila in del_grupo:
            numero += 1
            renglones.append(
                Renglon(
                    str(numero),
                    fila.partida,
                    fila.descripcion,
                    fila.unidad,
                    fila.cantidad,
                    _de_monto(fila.pu),
                    _de_monto(fila.total),
                )
            )
        subtotal = sum(
            (Decimal(f.total.exacto) for f in del_grupo if f.total is not None), Decimal(0)
        )
        grupos.append(Grupo(titulo, tuple(renglones), None if solo else _dinero(subtotal)))
    return tuple(grupos)


def _totales(total_exacto: str) -> tuple[LineaDeCierre, ...]:
    alicuota = Decimal(str(ALICUOTA_IVA.valor))
    impuestos = con_iva(Decimal(total_exacto), alicuota)
    return (
        LineaDeCierre("Subtotal sin IVA", _dinero(impuestos.subtotal)),
        LineaDeCierre(f"IVA ({_porcentaje(alicuota)} %)", _dinero(impuestos.iva)),
        LineaDeCierre("Total con IVA", _dinero(impuestos.total)),
    )


def _parametros(vivo: BorradorVivo) -> str:
    p = vivo.borrador.parametros
    return (
        f"FCAS {texto_de_cifra(p.fcas.normalize())} · Bono de alimentación "
        f"{texto_de_cifra(p.bono_alimentacion.normalize())} · Administración "
        f"{_porcentaje(p.administracion)} % · Utilidad {_porcentaje(p.utilidad)} %"
    )


def _apu(detalle: hoja_vista.DetalleDeApu, parametros: str) -> ApuDelPdf:
    return ApuDelPdf(
        codigo=detalle.codigo,
        descripcion=detalle.descripcion,
        unidad=detalle.unidad,
        rendimiento=detalle.rendimiento,
        parametros=parametros,
        tablas=tuple(
            TablaDeApu(
                grupo.rotulo,
                tuple(c.rotulo for c in grupo.columnas),
                tuple(
                    tuple(_celda(c.clave, fila.get(c.clave, "")) for c in grupo.columnas)
                    for fila in grupo.filas
                ),
                _de_monto(grupo.subtotal),
            )
            for grupo in detalle.grupos
        ),
        cierre=tuple(LineaDeCierre(f.concepto, _de_monto(f.monto)) for f in detalle.cierre),
    )


def documento_de_la_hoja(
    vivo: BorradorVivo,
    hoy: date,
    *,
    partida: str | None = None,
    agrupar: Agrupador = sin_agrupar,
) -> DocumentoPdf:
    """El documento del borrador vivo: el presupuesto y un APU por partida valorada; con
    `partida`, solo su APU (`PartidaSinApu` si no tiene uno valorado). Todo bajo el cerrojo del
    borrador: las cifras son las de un mismo `rev`."""
    with vivo.cerrojo:
        resumen = hoja_vista.resumen(vivo)
        vista = hoja_vista.vista_presupuesto(vivo)
        codigos = [p.codigo for p in hoja_vista.vista_apu(vivo).partidas]
        if partida is not None and partida not in codigos:
            raise PartidaSinApu(
                f"La partida «{partida}» no tiene un APU valorado en este borrador."
            )
        parametros = _parametros(vivo)
        apus = tuple(
            _apu(hoja_vista.vista_apu(vivo, codigo).detalle, parametros)
            for codigo in ([partida] if partida is not None else codigos)
        )
        fecha = vivo.borrador.fecha
    pendientes = sum(1 for f in vista.filas if f.pu is None)
    encabezado = Encabezado(
        titulo=TITULO_APU if partida is not None else TITULO_PRESUPUESTO,
        obra=vivo.proyecto,
        version=_version(vivo),
        fecha=f"{fecha:%d/%m/%Y}",
        emitido=f"{hoy:%d/%m/%Y}",
        moneda=vista.moneda,
        notas=_notas(vivo, resumen, pendientes),
    )
    if partida is not None:
        return DocumentoPdf(encabezado, (), (), (), apus)
    return DocumentoPdf(
        encabezado,
        _grupos(vista.filas, agrupar),
        _totales(vista.total.exacto),
        (
            "El IVA va sobre el total del presupuesto, nunca dentro del APU. Alícuota: "
            f"{ALICUOTA_IVA.fuente}.",
        ),
        apus,
    )


def nombre_del_pdf(codigo: str | None, *, partida: str | None = None) -> str:
    """`presupuesto_{código}.pdf` o `apu_{código}_{partida}.pdf`, con cada carácter fuera de
    A-Z a-z 0-9 . _ - cambiado por «_» y cada parte acotada (el recorte va antes)."""

    def seguro(texto: str) -> str:
        return _NO_SEGURO.sub("_", texto[:_LARGO_MAXIMO]) or "version"

    version = "borrador" if codigo is None else seguro(codigo)
    if partida is not None:
        return f"apu_{version}_{seguro(partida)}.pdf"
    return f"presupuesto_{version}.pdf"


# --- el dibujo -----------------------------------------------------------------------------------

_LETRA, _NEGRITA = "SiliceVera", "SiliceVera-Negrita"


def _registrar_letras() -> None:
    """La letra Vera que trae reportlab (licencia de Bitstream Vera), incrustada: dibuja las
    tildes, «m³» y «≤», que la Helvetica de la norma PDF no tiene (simulación de la bitácora)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if _LETRA not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_LETRA, "Vera.ttf"))
        pdfmetrics.registerFont(TTFont(_NEGRITA, "VeraBd.ttf"))


def _limpio(texto: str) -> str:
    return _PROHIBIDOS.sub("�", texto)


def pdf_en_bytes(documento: DocumentoPdf) -> bytes:
    """El PDF del documento, en carta vertical. Todo texto de la persona se escapa: un «<b>» en una
    descripción se ve tal cual, no se interpreta."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import (
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    _registrar_letras()
    e = documento.encabezado
    moneda = _limpio(e.moneda)
    normal = ParagraphStyle("normal", fontName=_LETRA, fontSize=8, leading=10)
    celda = ParagraphStyle("celda", parent=normal, fontSize=7.5, leading=9)
    negrita = ParagraphStyle("negrita", parent=celda, fontName=_NEGRITA)
    derecha = ParagraphStyle("derecha", parent=celda, alignment=TA_RIGHT)
    titulo = ParagraphStyle("titulo", parent=normal, fontName=_NEGRITA, fontSize=15, leading=19)
    subtitulo = ParagraphStyle("sub", parent=normal, fontName=_NEGRITA, fontSize=11, leading=14)
    rotulo = ParagraphStyle("rotulo", parent=normal, fontName=_NEGRITA, fontSize=9, leading=12)

    def p(texto: str, estilo=celda) -> Paragraph:
        return Paragraph(escape(_limpio(texto)), estilo)

    ancho = letter[0] - 3 * cm
    base = [
        ("FONT", (0, 0), (-1, -1), _LETRA, 7.5),
        ("FONT", (0, 0), (-1, 0), _NEGRITA, 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#a8a8a8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]

    def encabezado() -> list:
        partes = [
            p(e.titulo, titulo),
            p(e.obra, subtitulo),
            Spacer(1, 4),
            p(e.version, normal),
            p(f"Fecha del presupuesto: {e.fecha}", normal),
            p(f"Emitido el {e.emitido}", normal),
            p(f"Moneda: {e.moneda}", normal),
        ]
        partes += [p(nota, normal) for nota in e.notas]
        return [*partes, Spacer(1, 10)]

    def presupuesto() -> list:
        anchos = [0.9 * cm, 2.3 * cm, 5.6 * cm, 1.3 * cm, 2.0 * cm, 3.3 * cm, 3.1 * cm]
        filas: list[list] = [
            [
                "N°",
                "Código",
                "Descripción",
                "Unidad",
                "Cantidad",
                f"Precio unitario ({moneda})",
                f"Total ({moneda})",
            ]
        ]
        estilo = list(base) + [("ALIGN", (4, 0), (-1, -1), "RIGHT")]
        hay = any(g.renglones for g in documento.grupos)
        if not hay:
            filas.append([p(SIN_RENGLONES), "", "", "", "", "", ""])
            estilo.append(("SPAN", (0, 1), (-1, 1)))
        for grupo in documento.grupos if hay else ():
            if grupo.titulo:
                filas.append([p(grupo.titulo, negrita), "", "", "", "", "", ""])
                estilo.append(("SPAN", (0, len(filas) - 1), (-1, len(filas) - 1)))
            for r in grupo.renglones:
                filas.append(
                    [
                        r.numero,
                        p(r.partida),
                        p(r.descripcion),
                        p(r.unidad),
                        p(r.cantidad, derecha),
                        r.precio_unitario,
                        r.total,
                    ]
                )
            if grupo.subtotal is not None:
                filas.append(
                    [p(f"Subtotal de {grupo.titulo}", negrita), "", "", "", "", "", grupo.subtotal]
                )
                n = len(filas) - 1
                estilo += [("SPAN", (0, n), (-2, n)), ("FONT", (-1, n), (-1, n), _NEGRITA, 7.5)]
        tabla = Table(filas, colWidths=anchos, repeatRows=1)
        tabla.setStyle(TableStyle(estilo))
        totales = Table(
            [
                [p(t.concepto, negrita), p(f"{t.monto} {moneda}", derecha)]
                for t in documento.totales
            ],
            colWidths=[5 * cm, 4 * cm],
            hAlign="RIGHT",
        )
        totales.setStyle(TableStyle([("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black)]))
        notas = [p(n, normal) for n in documento.notas_finales]
        return [tabla, Spacer(1, 8), KeepTogether([totales]), Spacer(1, 8), *notas]

    def apu(a: ApuDelPdf) -> list:
        partes = [
            p(TITULO_APU, subtitulo),
            p(f"{a.codigo} · {a.descripcion}", rotulo),
            p(f"Unidad: {a.unidad} · Rendimiento: {a.rendimiento} {a.unidad} por día", normal),
            p(a.parametros, normal),
            Spacer(1, 6),
        ]
        for t in a.tablas:
            columnas = len(t.columnas)
            filas: list[list] = [list(t.columnas)]
            estilo = list(base) + [("ALIGN", (1, 0), (-1, -1), "RIGHT")]
            if not t.filas:
                filas.append([p(SIN_LINEAS)] + [""] * (columnas - 1))
                estilo.append(("SPAN", (0, 1), (-1, 1)))
            filas += [[p(c) if i == 0 else c for i, c in enumerate(f)] for f in t.filas]
            filas.append([p(POR_UNIDAD, negrita)] + [""] * (columnas - 2) + [f"{t.subtotal}"])
            n = len(filas) - 1
            estilo += [("SPAN", (0, n), (-2, n)), ("FONT", (-1, n), (-1, n), _NEGRITA, 7.5)]
            resto = (ancho - 7.5 * cm) / max(columnas - 1, 1)
            tabla = Table(filas, colWidths=[7.5 * cm] + [resto] * (columnas - 1), repeatRows=1)
            tabla.setStyle(TableStyle(estilo))
            partes += [p(t.rotulo, rotulo), tabla, Spacer(1, 6)]
        cierre = Table(
            [[p(c.concepto, celda), p(f"{c.monto} {moneda}", derecha)] for c in a.cierre],
            colWidths=[6 * cm, 4 * cm],
            hAlign="RIGHT",
        )
        cierre.setStyle(TableStyle([("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black)]))
        return [*partes, p("Cierre", rotulo), cierre]

    historia = encabezado()
    if documento.grupos or documento.totales:
        historia += presupuesto()
    for n, a in enumerate(documento.apus):
        if n or documento.grupos or documento.totales:
            historia.append(PageBreak())
        historia += apu(a)

    pie = _limpio(f"Sílice · {e.obra} · {e.version}")

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
        title=_limpio(f"{e.titulo} · {e.obra}"),
        author="Sílice",
        creator="Sílice",
    ).build(historia, canvasmaker=_Numerado)
    return salida.getvalue()
