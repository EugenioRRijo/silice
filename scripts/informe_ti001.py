"""Informe PDF del caso TI-001: APU, presupuesto, plan, curva, punto de equilibrio y auditoría.

Los datos del caso están en `tests/fixtures/caso_ti001.py`; el cálculo adicional (recálculo,
pruebas de control, sensibilidad, punto de equilibrio) en `scripts/analisis_ti001.py`; la
auditoría del programa del 30/09/2026 en `scripts/auditoria_ti001.py`. Necesita el extra
`informes` (reportlab y matplotlib).

Uso::

    uv run --extra informes python scripts/informe_ti001.py --salida TI-001_informe.pdf
"""

from __future__ import annotations

import argparse
import io
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    CondPageBreak,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.verification.directivas import codigos_en_etiqueta  # noqa: E402
from scripts import analisis_ti001 as an  # noqa: E402
from scripts import auditoria_ti001 as ap  # noqa: E402
from tests.fixtures import caso_ti001 as caso  # noqa: E402

SALIDA_POR_DEFECTO = "TI-001_informe.pdf"


# Paleta (instancia de referencia, modo claro): 3 primeras ranuras categoricas
AZUL, NARANJA, AGUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, REJILLA = "#0b0b0b", "#52514e", "#e2e1dc"
C_AZUL = colors.HexColor(AZUL)
C_CAB = colors.HexColor("#1f3b5c")
C_SUAVE = colors.HexColor("#eef3fa")
C_LINEA = colors.HexColor("#c9ced6")
C_OK = colors.HexColor("#e7f5ee")
C_MAL = colors.HexColor("#fdecea")

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.edgecolor": REJILLA,
        "axes.labelcolor": TINTA2,
        "xtick.color": TINTA2,
        "ytick.color": TINTA2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": REJILLA,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "legend.frameon": False,
    }
)


# ---------------------------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------------------------


def f(valor, dec: int = 2) -> str:
    """Decimal -> '12 345,67' (redondeo solo al presentar)."""
    if valor is None:
        return ""
    q = Decimal(valor).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)
    signo = "-" if q < 0 else ""
    entero, _, frac = f"{abs(q):.{dec}f}".partition(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    texto = " ".join(grupos)
    return f"{signo}{texto},{frac}" if dec else f"{signo}{texto}"


def cant(valor) -> str:
    d = Decimal(valor).normalize()
    dec = max(0, -d.as_tuple().exponent)
    return f(valor, min(dec, 4))


ss = getSampleStyleSheet()
H1 = ParagraphStyle(
    "H1", parent=ss["Heading1"], fontSize=15, textColor=C_CAB, spaceBefore=4, spaceAfter=6
)
H2 = ParagraphStyle(
    "H2", parent=ss["Heading2"], fontSize=11.5, textColor=C_CAB, spaceBefore=8, spaceAfter=4
)
H3 = ParagraphStyle(
    "H3", parent=ss["Heading3"], fontSize=9.5, textColor=C_CAB, spaceBefore=6, spaceAfter=2
)
P = ParagraphStyle("P", parent=ss["BodyText"], fontSize=8.6, leading=11.2, spaceAfter=4)
PS = ParagraphStyle("PS", parent=P, fontSize=7.4, leading=9.2, textColor=colors.HexColor(TINTA2))
CEL = ParagraphStyle("CEL", parent=P, fontSize=7.2, leading=8.6, spaceAfter=0)
CELB = ParagraphStyle("CELB", parent=CEL, fontName="Helvetica-Bold")
CELW = ParagraphStyle("CELW", parent=CEL, fontName="Helvetica-Bold", textColor=colors.white)


def c(texto, estilo=CEL):
    return Paragraph(str(texto), estilo)


def tabla(filas, anchos, cab=True, num_cols=(), total=False, zebra=True, extra=None):
    datos = [
        [
            c(x, CELW) if (cab and i == 0) else (x if isinstance(x, Paragraph) else c(x))
            for x in fila
        ]
        for i, fila in enumerate(filas)
    ]
    t = Table(datos, colWidths=anchos, repeatRows=1 if cab else 0)
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, C_LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    if cab:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), C_CAB))
    if zebra:
        for i in range(1 if cab else 0, len(filas)):
            if i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), C_SUAVE))
    if total:
        estilo.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dde6f2")))
    t.setStyle(TableStyle(estilo + (extra or [])))
    for col in num_cols:
        for fila in datos[1 if cab else 0 :]:
            if isinstance(fila[col], Paragraph):
                fila[col].style = ParagraphStyle("n", parent=fila[col].style, alignment=2)
    return t


def figura(fig, ancho_mm=175):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    w, h = fig.get_size_inches()
    ancho = ancho_mm * mm
    return Image(buf, width=ancho, height=ancho * h / w)


def nombre_periodo(etiqueta: str) -> str:
    return etiqueta.split(" [")[0]


def construir(salida: Path) -> Path:
    """Arma el PDF completo en `salida` y devuelve la ruta."""
    orden = caso.ORDEN
    frente = caso.FRENTE
    # ---------------------------------------------------------------------------------------------
    # Datos
    # ---------------------------------------------------------------------------------------------

    res = an.elaboracion()
    pres = res.presupuesto
    inf = res.informe
    grupos = an.por_partida(pres)
    pe = an.punto_equilibrio(pres)
    controles = an.pruebas_de_control()
    sens = an.sensibilidad(pres)
    verif = an.verificaciones_motor(pres)
    par = caso.PARAMETROS
    num = {codigo: f"{i:02d}" for i, codigo in enumerate(orden, start=1)}
    cd_total = sum(
        (g["cantidad"] * g["resultado"].costo_directo for g in grupos.values()), Decimal(0)
    )
    n_graves = sum(1 for h in inf.hallazgos if h.severidad >= 3)
    detectados = sum(1 for x in controles if x["ok"])

    # ---------------------------------------------------------------------------------------------
    # Graficas
    # ---------------------------------------------------------------------------------------------

    def g_composicion():
        datos = sorted(((g["total"], k) for k, g in grupos.items()), reverse=False)
        fig, ax = plt.subplots(figsize=(7.2, 3.1))
        ys = range(len(datos))
        vals = [float(v) for v, _ in datos]
        ax.barh(ys, vals, color=AZUL, height=0.62)
        ax.set_yticks(list(ys), [f"{k}" for _, k in datos])
        for y, v in zip(ys, vals, strict=True):
            ax.text(
                v + max(vals) * 0.01,
                y,
                f"{f(Decimal(v))}  ({v / float(pres.total) * 100:.1f} %)",
                va="center",
                fontsize=7.5,
                color=TINTA,
            )
        ax.set_xlim(0, max(vals) * 1.28)
        ax.set_xlabel("USD")
        ax.grid(axis="y", visible=False)
        ax.set_title(
            "Peso de cada partida en el presupuesto", loc="left", fontsize=9.5, color=TINTA
        )
        return figura(fig)

    def g_gantt():
        fig, ax = plt.subplots(figsize=(7.2, 3.2))
        colores = {"Cuadrilla electrica": AZUL, "Tecnico de redes": NARANJA}
        filas = list(reversed(orden))
        for dia, (_etiqueta, reparto) in enumerate(caso.PLAN):
            for codigo, frac in reparto:
                y = filas.index(codigo)
                ax.barh(y, 0.94, left=dia + 0.03, color=colores[frente[codigo]], height=0.6)
                ax.text(
                    dia + 0.5,
                    y,
                    f"{float(frac) * 100:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color="white",
                )
        ax.set_yticks(range(len(filas)), filas)
        ax.set_xticks([i + 0.5 for i in range(len(caso.PLAN))], [e for e, _ in caso.PLAN])
        ax.set_xlim(0, len(caso.PLAN))
        ax.grid(axis="y", visible=False)
        from matplotlib.patches import Patch

        ax.legend(
            handles=[Patch(color=col, label=nombre) for nombre, col in colores.items()],
            loc="upper center",
            bbox_to_anchor=(0.5, -0.1),
            ncol=2,
            fontsize=7.5,
        )
        ax.set_title(
            "Plan de trabajo (fraccion de cada partida ejecutada por dia)",
            loc="left",
            fontsize=9.5,
            color=TINTA,
        )
        return figura(fig)

    def g_curva():
        dias = [nombre_periodo(p.periodo) for p in pres.curva]
        acum = [float(p.acumulado) for p in pres.curva]
        montos = [float(p.monto) for p in pres.curva]
        x = list(range(1, len(dias) + 1))
        fig, (a1, a2) = plt.subplots(
            2, 1, figsize=(7.2, 5.6), sharex=True, gridspec_kw={"height_ratios": [1.6, 1]}
        )
        a1.plot(
            [0] + x,
            [0] + acum,
            color=AZUL,
            linewidth=2,
            marker="o",
            markersize=4.5,
            label="Inversion acumulada",
        )
        pev = float(pe["PE"])
        a1.axhline(pev, color=NARANJA, linewidth=1.2, linestyle="--")
        a1.text(
            0.1,
            pev + float(pres.total) * 0.02,
            f"Punto de equilibrio {f(pe['PE'])} USD ({float(pe['PE_pct']):.1f} %)",
            color=TINTA,
            fontsize=7.5,
        )
        # interpolacion del cruce
        dia_pe = dias.index(nombre_periodo(pe["periodo"])) + 1
        x_pe = dia_pe - 1 + float(pe["fraccion_periodo"])
        a1.plot(
            [x_pe],
            [pev],
            marker="o",
            markersize=8,
            color=NARANJA,
            markeredgecolor="white",
            markeredgewidth=1.5,
        )
        a1.annotate(
            f"{nombre_periodo(pe['periodo'])} ({float(pe['fraccion_periodo']) * 100:.0f} % del dia)",
            (x_pe, pev),
            xytext=(x_pe + 0.35, pev - float(pres.total) * 0.12),
            fontsize=7.5,
            color=TINTA,
            arrowprops={"arrowstyle": "-", "color": TINTA2, "lw": 0.6},
        )
        a1.text(
            x[-1],
            acum[-1] * 1.03,
            f"{f(pres.total_curva)} USD (100 %)",
            ha="right",
            fontsize=7.5,
            color=TINTA,
        )
        a1.set_ylim(0, float(pres.total) * 1.12)
        a1.set_ylabel("USD acumulados")
        a1.set_title(
            "Curva de inversion (S) y punto de equilibrio", loc="left", fontsize=9.5, color=TINTA
        )
        a2.bar(x, montos, color=AZUL, width=0.62)
        for xi, v in zip(x, montos, strict=True):
            a2.text(
                xi, v + max(montos) * 0.03, f(Decimal(v), 0), ha="center", fontsize=6.8, color=TINTA
            )
        a2.set_ylim(0, max(montos) * 1.2)
        a2.set_ylabel("USD por dia")
        a2.set_xticks(x, dias)
        a2.grid(axis="x", visible=False)
        a2.set_title("Inversion por periodo", loc="left", fontsize=9, color=TINTA)
        fig.tight_layout()
        return figura(fig)

    def g_equilibrio():
        v, cv, cf = float(pe["V"]), float(pe["CV"]), float(pe["CF"])
        xs = [0, 100]
        fig, ax = plt.subplots(figsize=(7.2, 3.6))
        ax.plot(
            xs, [0, v], color=AZUL, linewidth=2, label="Ingresos (valuaciones a precio de contrato)"
        )
        ax.plot(
            xs, [cf, cf + cv], color=NARANJA, linewidth=2, label="Costo total = fijo + variable"
        )
        ax.plot(
            xs,
            [cf, cf],
            color=TINTA2,
            linewidth=1.2,
            linestyle="--",
            label="Costo fijo (administracion)",
        )
        xp = float(pe["PE_pct"])
        ax.plot(
            [xp],
            [float(pe["PE"])],
            marker="o",
            markersize=8,
            color=AGUA,
            markeredgecolor="white",
            markeredgewidth=1.5,
        )
        ax.annotate(
            f"Equilibrio: {xp:.1f} % de ejecucion\n{f(pe['PE'])} USD",
            (xp, float(pe["PE"])),
            xytext=(xp - 43, float(pe["PE"]) + v * 0.18),
            fontsize=7.5,
            color=TINTA,
            arrowprops={"arrowstyle": "-", "color": TINTA2, "lw": 0.6},
        )
        ax.fill_between(
            [xp, 100], [float(pe["PE"]), v], [float(pe["PE"]), cf + cv], color=AGUA, alpha=0.12
        )
        ax.annotate(
            f"Utilidad al 100 %: {f(pe['U'])} USD",
            (99, (v + cf + cv) / 2),
            xytext=(62, v * 0.97),
            fontsize=7.3,
            color=TINTA,
            arrowprops={"arrowstyle": "-", "color": TINTA2, "lw": 0.6},
        )
        ax.set_xlim(0, 100)
        ax.set_ylim(0, v * 1.08)
        ax.set_xlabel("Avance valuado del contrato (%)")
        ax.set_ylabel("USD")
        ax.legend(loc="upper left", fontsize=7.3)
        ax.set_title("Punto de equilibrio del contrato", loc="left", fontsize=9.5, color=TINTA)
        return figura(fig)

    # ---------------------------------------------------------------------------------------------
    # Documento
    # ---------------------------------------------------------------------------------------------

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(TINTA2))
        canvas.drawString(
            15 * mm,
            9 * mm,
            "TI-001 - Instalacion de laptops HP, canalizacion, cableado y servidor en rack - Analisis de precios auditado",
        )
        canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Pagina {doc.page}")
        canvas.setStrokeColor(C_LINEA)
        canvas.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)
        canvas.restoreState()

    flujo = []
    ancho = A4[0] - 30 * mm

    # Portada ------------------------------------------------------------------------------------
    flujo += [Spacer(1, 18 * mm)]
    flujo += [
        Paragraph(
            "Analisis de Precios Unitarios auditado",
            ParagraphStyle("t0", parent=H1, fontSize=22, leading=26),
        )
    ]
    flujo += [
        Paragraph(
            "Instalacion de 12 laptops HP con red cableada Cat 6, canalizacion EMT y servidor en rack",
            ParagraphStyle(
                "t1", parent=H2, fontSize=13, leading=16, textColor=colors.HexColor(TINTA)
            ),
        )
    ]
    flujo += [Spacer(1, 4 * mm)]
    flujo += [
        Paragraph(
            f"Presupuesto <b>{caso.CODIGO}</b> - fecha {caso.FECHA:%d/%m/%Y} - moneda USD - plazo 10 dias habiles",
            P,
        )
    ]
    flujo += [Spacer(1, 6 * mm)]
    kpis = [
        ["Precio total del contrato", f"{f(pres.total)} USD"],
        ["Costo directo", f"{f(cd_total)} USD"],
        ["Partidas / renglones de computo", f"{len(grupos)} / {len(pres.partidas)}"],
        ["Cierre de la curva de inversion", f"{f(pres.total_curva)} USD (100,00 %)"],
        [
            "Punto de equilibrio",
            f"{f(pe['PE'])} USD - {f(pe['PE_pct'])} % del contrato - {nombre_periodo(pe['periodo'])}",
        ],
        [
            "Auditoria automatica (7 reglas)",
            f"{'CUMPLE' if inf.cumple else 'NO CUMPLE'} - {n_graves} errores, {len(inf.hallazgos)} avisos informativos",
        ],
        [
            "Pruebas de control de la auditoria",
            f"{detectados} de {len(controles)} errores sembrados detectados",
        ],
        ["Auditoria del programa", ap.VEREDICTO_CORTO],
    ]
    t = Table([[c(k, CELB), c(v)] for k, v in kpis], colWidths=[62 * mm, ancho - 62 * mm])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, C_LINEA),
                ("BACKGROUND", (0, 0), (0, -1), C_SUAVE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    flujo += [t, Spacer(1, 8 * mm)]
    flujo += [
        Paragraph(
            "<b>Naturaleza de los datos.</b> Caso construido con fines academicos: la oficina, la topologia de red, "
            "los rendimientos y el plan son supuestos declarados; no es una obra ejecutada. Los precios de los insumos "
            "son referencias publicadas: listados MaPreX v26.0.0.1 de julio de 2026 (materiales y equipos al 09/07/2026; "
            "mano de obra al 01/07/2026), convertidos de bolivares a USD con la tasa que declara el propio listado, "
            "633,3644 Bs/USD al 01/07/2026. Las laptops y el servidor HP se valoran con la referencia de categoria de "
            "MaPreX (laptop i7, OFI058; servidor en rack i7, OFI131), no con una cotizacion de HP: ver la seccion de sensibilidad.",
            PS,
        ),
        Paragraph(
            "Calculado con el sistema de generacion y auditoria de APU (motor puro en Decimal, sin redondeos intermedios; "
            "redondeo a 2 decimales solo al presentar). Cantidades extraidas de <i>topologia_oficina.csv</i> por el adaptador "
            "telecom; auditoria de las siete reglas R1-R7 generada siempre.",
            PS,
        ),
    ]
    flujo += [PageBreak()]

    # 1. Resumen ejecutivo -----------------------------------------------------------------------
    flujo += [Paragraph("1. Resumen ejecutivo", H1)]
    lap = grupos["TI-LAP"]
    peso_equipos = (
        (
            grupos["TI-LAP"]["total"]
            + grupos["TI-SRV"]["total"]
            + grupos["TI-SW"]["total"]
            + grupos["TI-UPS"]["total"]
            + grupos["TI-RACK"]["total"]
        )
        / pres.total
        * 100
    )
    flujo += [
        Paragraph(
            f"El contrato vale <b>{f(pres.total)} USD</b>. De ese total, {f(peso_equipos, 1)} % es suministro de equipos "
            f"(laptops, servidor, switch, UPS y rack) y el resto es infraestructura pasiva: canalizacion EMT, salidas "
            f"de datos, cable UTP Cat 6 y certificacion. Solo las 12 laptops suman {f(lap['total'])} USD "
            f"({f(lap['total'] / pres.total * 100, 1)} %), asi que su precio de referencia es el supuesto que mas pesa.",
            P,
        ),
        Paragraph(
            f"La auditoria automatica <b>{'cumple' if inf.cumple else 'no cumple'}</b>: ninguna de las siete reglas encuentra errores. "
            f"Los {len(inf.hallazgos)} avisos informativos son de R4. El adaptador guarda el origen y el destino de cada tramo "
            "como especificaciones tecnicas, y R4 no los encuentra en el texto del APU. Se registra como hallazgo del programa "
            "(ver la seccion 2).",
            P,
        ),
        Paragraph(
            f"Se sembraron {len(controles)} errores conocidos para probar la auditoria y se detectaron {detectados}. "
            "El que se escapa revela un defecto de R4, que compara especificaciones por subcadena. "
            f"El punto de equilibrio llega con el {f(pe['PE_pct'])} % del contrato valuado, "
            f"durante el {nombre_periodo(pe['periodo'])} del plan.",
            P,
        ),
    ]
    flujo += [g_composicion()]

    # 2. Auditoria del programa ------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("2. Auditoria del programa", H1)]
    for parrafo in ap.RESUMEN:
        flujo += [Paragraph(parrafo, P)]
    flujo += [Paragraph("2.1 Comprobaciones automaticas", H2)]
    flujo += [
        tabla([["Comprobacion", "Resultado"]] + ap.COMPROBACIONES, [95 * mm, ancho - 95 * mm])
    ]
    flujo += [Paragraph("2.2 Hallazgos", H2)]
    flujo += [
        tabla(
            [["#", "Sev.", "Donde", "Hallazgo y escenario", "Recomendacion"]] + ap.HALLAZGOS,
            [8 * mm, 15 * mm, 34 * mm, 72 * mm, ancho - 129 * mm],
        )
    ]
    if ap.FORTALEZAS:
        flujo += [Paragraph("2.3 Fortalezas", H2)]
        for x in ap.FORTALEZAS:
            flujo += [Paragraph(f"- {x}", P)]

    # 3. Premisas --------------------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("3. Premisas del calculo", H1)]
    flujo += [
        tabla(
            [
                ["Parametro", "Valor", "Fuente / criterio"],
                [
                    "Tasa de cambio",
                    "633,3644 Bs/USD",
                    "Declarada en el listado MaPreX de mano de obra (01/07/2026)",
                ],
                [
                    "FCAS (prestaciones)",
                    f"{f(par.fcas * 100, 0)} %",
                    "Parametro por defecto del sistema (decision D4: sin fuente normativa)",
                ],
                [
                    "Bono de alimentacion",
                    f"{f(par.bono_alimentacion, 4)} USD/obrero-dia",
                    "Bono MaPreX del electricista de 1ra N5 (19-215); el contrato admite un bono unico",
                ],
                ["Administracion", f"{f(par.administracion * 100, 0)} %", "Sobre el costo directo"],
                [
                    "Utilidad",
                    f"{f(par.utilidad * 100, 0)} %",
                    "En cascada sobre costo directo + administracion (factor 1,265)",
                ],
                [
                    "Rendimientos",
                    "Estimados",
                    "Supuestos declarados del caso; no son rendimientos medidos en obra",
                ],
                [
                    "Equipos",
                    "Precio x factor",
                    "Factor Cop/Depr. de equipos.pdf (1,0 = alquiler diario)",
                ],
                [
                    "Laptops y servidor",
                    "Suministro",
                    "Entran como material (se entregan al cliente); precio de adquisicion de equipos.pdf",
                ],
            ],
            [38 * mm, 36 * mm, ancho - 74 * mm],
        )
    ]
    flujo += [
        Paragraph("Formula aplicada (especificacion del sistema, sin redondeos intermedios)", H3)
    ]
    flujo += [
        Paragraph(
            "materiales = suma(cantidad x precio), sin dividir entre el rendimiento - equipos = suma(cantidad x precio x depreciacion) / rendimiento - "
            "mano de obra = [suma(obreros x jornal x (1 + FCAS)) + bono x obreros] / rendimiento - costo directo = materiales + equipos + mano de obra - "
            "precio unitario = costo directo x 1,15 x 1,10.",
            P,
        )
    ]
    flujo += [Paragraph("Supuestos de ingenieria", H3)]
    for s in [
        "Oficina de una planta con cuarto tecnico: zona A (6 puestos), zona B (5 puestos) y recepcion (1 puesto, impresora y 1 salida de reserva). Son 14 salidas de datos: 12 puestos + 2.",
        "Troncales EMT de 1 pulg desde el cuarto tecnico, porque por una de 3/4 pulg no caben seis cables Cat 6 con 40 % de ocupacion. Bajantes EMT de 3/4 pulg de 3 m por salida. Reserva de canalizacion: 5 %.",
        "Un tramo UTP Cat 6 por salida, desde el rack, sin empalmes. Reserva del 10 % (curvas y holgura en el rack y en la salida). Cada enlace permanente se certifica y se etiqueta en los dos extremos.",
        "Rack de piso cerrado 42U. Aloja el patch panel de 24 puertos, el switch administrable de 48 puertos, la UPS de 3000 VA y el servidor.",
        "Los rendimientos, en unidades por dia, se leen en cada APU. Dos frentes trabajan en paralelo: la cuadrilla electrica y el tecnico de redes.",
    ]:
        flujo += [Paragraph(f"- {s}", P)]

    # 4. Computos ---------------------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("4. Computos metricos trazables", H1)]
    flujo += [
        Paragraph(
            "Cada cantidad sale de una fila de <i>topologia_oficina.csv</i> (origen_id). Los tramos se calculan con la regla parametrica del adaptador, <i>longitud_m x (1 + reserva)</i>, y R1 la vuelve a evaluar. Las cantidades de salidas y certificaciones las comprueba R5 con los balances {TI-LAP} + 2 y {TI-PTO}.",
            P,
        )
    ]
    filas = [["Origen", "Tipo", "Partida", "Descripcion", "Regla / parametros", "Cantidad", "Und"]]
    for p in sorted(
        pres.partidas, key=lambda x: (orden.index(x.item.codigo_partida), x.item.origen_id)
    ):
        it = p.item
        regla = (
            f"{f(it.parametros['longitud_m'], 1)} x (1 + {f(it.parametros['reserva'], 2)})"
            if it.regla
            else (
                "balance " + it.especificaciones["_balance"]
                if "_balance" in it.especificaciones
                else "tabular"
            )
        )
        filas.append(
            [
                it.origen_id,
                it.origen_tipo.value,
                it.codigo_partida,
                it.descripcion,
                regla,
                cant(it.cantidad),
                it.unidad,
            ]
        )
    flujo += [
        tabla(
            filas,
            [18 * mm, 13 * mm, 17 * mm, 64 * mm, 34 * mm, 17 * mm, ancho - 163 * mm],
            num_cols=(5,),
        )
    ]

    # 5. Presupuesto -----------------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("5. Presupuesto", H1)]
    filas = [["N.", "Codigo", "Descripcion", "Und", "Cantidad", "P.U. (USD)", "Total (USD)", "%"]]
    for codigo in orden:
        g = grupos[codigo]
        filas.append(
            [
                num[codigo],
                codigo,
                g["apu"].descripcion,
                g["apu"].unidad,
                cant(g["cantidad"]),
                f(g["resultado"].precio_unitario),
                f(g["total"]),
                f(g["total"] / pres.total * 100),
            ]
        )
    filas.append(
        [
            "",
            "",
            c("TOTAL DEL PRESUPUESTO (incluye administracion 15 % y utilidad 10 %)", CELB),
            "",
            "",
            "",
            c(f(pres.total), CELB),
            "100,00",
        ]
    )
    flujo += [
        tabla(
            filas,
            [8 * mm, 17 * mm, 72 * mm, 11 * mm, 16 * mm, 19 * mm, 22 * mm, ancho - 165 * mm],
            num_cols=(4, 5, 6, 7),
            total=True,
        )
    ]
    flujo += [Spacer(1, 3 * mm)]
    cd_mat = sum((g["cantidad"] * g["resultado"].materiales for g in grupos.values()), Decimal(0))
    cd_eq = sum((g["cantidad"] * g["resultado"].equipos for g in grupos.values()), Decimal(0))
    cd_mo = sum((g["cantidad"] * g["resultado"].mano_obra for g in grupos.values()), Decimal(0))
    filas = [
        ["Estructura del precio", "USD", "%"],
        ["Materiales y suministros", f(cd_mat), f(cd_mat / pres.total * 100)],
        ["Equipos y herramientas", f(cd_eq), f(cd_eq / pres.total * 100)],
        ["Mano de obra (con FCAS y bono)", f(cd_mo), f(cd_mo / pres.total * 100)],
        ["Costo directo", f(cd_total), f(cd_total / pres.total * 100)],
        ["Administracion (15 % del costo directo)", f(pe["CF"]), f(pe["CF"] / pres.total * 100)],
        [
            "Utilidad (10 % de costo directo + administracion)",
            f(pe["U"]),
            f(pe["U"] / pres.total * 100),
        ],
        ["Total", f(pres.total), "100,00"],
    ]
    flujo += [tabla(filas, [95 * mm, 35 * mm, 25 * mm], num_cols=(1, 2), total=True)]

    # 6. APU ------------------------------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("6. Analisis de precios unitarios", H1)]
    for codigo in orden:
        g = grupos[codigo]
        apu, r = g["apu"], g["resultado"]
        bloque = [CondPageBreak(95 * mm)]
        cab = Table(
            [
                [
                    c(f"<b>Partida {num[codigo]} - {codigo}</b>", CELW),
                    c(f"Unidad: <b>{apu.unidad}</b>", CELW),
                    c(f"Rendimiento: <b>{cant(apu.rendimiento)} {apu.unidad}/dia</b>", CELW),
                    c(f"Cantidad: <b>{cant(g['cantidad'])}</b>", CELW),
                ],
                [c(apu.descripcion, CELB), "", "", ""],
            ],
            colWidths=[62 * mm, 30 * mm, 50 * mm, ancho - 142 * mm],
        )
        cab.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), C_CAB),
                    ("SPAN", (0, 1), (-1, 1)),
                    ("BACKGROUND", (0, 1), (-1, 1), C_SUAVE),
                    ("GRID", (0, 0), (-1, -1), 0.25, C_LINEA),
                ]
            )
        )
        bloque.append(cab)
        if apu.materiales:
            filas = [
                ["1. Materiales y suministros (Ref. MaPreX)", "Und", "Cantidad", "Precio", "Total"]
            ]
            for linea in apu.materiales:
                filas.append(
                    [
                        linea.descripcion,
                        linea.unidad,
                        cant(linea.cantidad),
                        f(linea.precio, 4),
                        f(linea.total, 4),
                    ]
                )
            filas.append(
                [
                    c("Total materiales (no se divide entre el rendimiento)", CELB),
                    "",
                    "",
                    "",
                    c(f(r.materiales, 4), CELB),
                ]
            )
            bloque.append(
                tabla(
                    filas,
                    [100 * mm, 14 * mm, 18 * mm, 24 * mm, ancho - 156 * mm],
                    num_cols=(2, 3, 4),
                    total=True,
                    zebra=False,
                )
            )
        if apu.equipos:
            filas = [["2. Equipos", "Cantidad", "Precio", "Deprec.", "Total"]]
            tot = Decimal(0)
            for linea in apu.equipos:
                tot += linea.total
                filas.append(
                    [
                        linea.descripcion,
                        cant(linea.cantidad),
                        f(linea.precio, 4),
                        cant(linea.depreciacion),
                        f(linea.total, 4),
                    ]
                )
            filas.append(
                [
                    c(f"Total equipos / rendimiento = {f(tot, 4)} / {cant(apu.rendimiento)}", CELB),
                    "",
                    "",
                    "",
                    c(f(r.equipos, 4), CELB),
                ]
            )
            bloque.append(
                tabla(
                    filas,
                    [100 * mm, 18 * mm, 22 * mm, 16 * mm, ancho - 156 * mm],
                    num_cols=(1, 2, 3, 4),
                    total=True,
                    zebra=False,
                )
            )
        if apu.mano_obra:
            filas = [["3. Mano de obra (jornal MaPreX)", "Obreros", "Jornal", "Total"]]
            suma = Decimal(0)
            for linea in apu.mano_obra:
                suma += linea.total
                filas.append(
                    [linea.descripcion, cant(linea.cantidad), f(linea.sueldo, 4), f(linea.total, 4)]
                )
            obreros = apu.total_obreros
            con_fcas = suma * (1 + par.fcas)
            bono = par.bono_alimentacion * obreros
            filas.append(
                [c(f"Jornales x (1 + FCAS {f(par.fcas * 100, 0)} %)", CEL), "", "", f(con_fcas, 4)]
            )
            filas.append(
                [
                    c(
                        f"Bono de alimentacion {f(par.bono_alimentacion, 4)} x {cant(obreros)} obreros",
                        CEL,
                    ),
                    "",
                    "",
                    f(bono, 4),
                ]
            )
            filas.append(
                [
                    c(
                        f"Total mano de obra / rendimiento = {f(con_fcas + bono, 4)} / {cant(apu.rendimiento)}",
                        CELB,
                    ),
                    "",
                    "",
                    c(f(r.mano_obra, 4), CELB),
                ]
            )
            bloque.append(
                tabla(
                    filas,
                    [116 * mm, 18 * mm, 22 * mm, ancho - 156 * mm],
                    num_cols=(1, 2, 3),
                    total=True,
                    zebra=False,
                )
            )
        adm = r.con_administracion - r.costo_directo
        uti = r.precio_unitario - r.con_administracion
        res_t = Table(
            [
                [
                    c("Costo directo por unidad"),
                    c(f(r.costo_directo, 4)),
                    c("Administracion 15 %"),
                    c(f(adm, 4)),
                ],
                [c("Subtotal"), c(f(r.con_administracion, 4)), c("Utilidad 10 %"), c(f(uti, 4))],
                [
                    c("<b>PRECIO UNITARIO</b>", CELB),
                    c(f"<b>{f(r.precio_unitario)} USD/{apu.unidad}</b>", CELB),
                    c("Total partida", CELB),
                    c(f"<b>{f(g['total'])} USD</b>", CELB),
                ],
            ],
            colWidths=[46 * mm, 44 * mm, 46 * mm, ancho - 136 * mm],
        )
        res_t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, C_LINEA),
                    ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#dde6f2")),
                ]
            )
        )
        bloque += [res_t, Spacer(1, 5 * mm)]
        flujo += bloque

    # 7. Plan de trabajo ------------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("7. Plan de trabajo", H1)]
    flujo += [
        Paragraph(
            "Dos frentes en paralelo: la cuadrilla electrica (canalizacion, salidas, cableado y UPS) y el tecnico de redes (rack, switch, servidor, laptops y certificacion). La certificacion va al final porque necesita el cableado terminado.",
            P,
        )
    ]
    flujo += [g_gantt()]
    cab_fila = ["Partida"] + [e.replace("Dia ", "D") for e, _ in caso.PLAN] + ["Total"]
    filas = [cab_fila]
    for codigo in orden:
        fila = [codigo]
        total = Decimal(0)
        for _, reparto in caso.PLAN:
            v = dict(reparto).get(codigo)
            total += v or 0
            fila.append(f"{f(v * 100, 0)}%" if v else "")
        fila.append(f"{f(total * 100, 0)}%")
        filas.append(fila)
    flujo += [
        Spacer(1, 2 * mm),
        tabla(
            filas,
            [22 * mm] + [13.5 * mm] * 10 + [ancho - 22 * mm - 135 * mm],
            num_cols=tuple(range(1, 12)),
        ),
    ]

    # 8. Curva de inversion ---------------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("8. Curva de inversion", H1)]
    flujo += [
        Paragraph(
            "El monto de cada dia es la suma de fraccion x total de cada partida que se ejecuta ese dia. El ultimo periodo se calcula como el total menos lo ya repartido, asi que la curva cierra por construccion en el total exacto del presupuesto, y R2 y R7 lo comprueban.",
            P,
        )
    ]
    filas = [["Periodo", "Partidas", "Monto (USD)", "Acumulado (USD)", "% acumulado"]]
    for pt in pres.curva:
        filas.append(
            [
                nombre_periodo(pt.periodo),
                ", ".join(codigos_en_etiqueta(pt.periodo)),
                f(pt.monto),
                f(pt.acumulado),
                f(pt.acumulado / pres.total * 100),
            ]
        )
    flujo += [
        tabla(filas, [18 * mm, 72 * mm, 28 * mm, 30 * mm, ancho - 148 * mm], num_cols=(2, 3, 4))
    ]
    flujo += [Spacer(1, 3 * mm), g_curva()]

    # 9. Punto de equilibrio --------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("9. Punto de equilibrio", H1)]
    flujo += [
        Paragraph(
            "El costo directo (materiales, equipos y mano de obra) se trata como costo variable: crece con cada unidad ejecutada. "
            "La administracion (gastos generales, oficina, gerencia, seguros) se trata como costo fijo del contrato. "
            "El margen de contribucion es la parte de cada dolar valuado que queda despues de pagar el costo variable. "
            "El punto de equilibrio es la valuacion acumulada que cubre el costo fijo.",
            P,
        )
    ]
    filas = [
        ["Concepto", "Formula", "Valor"],
        ["Ingresos del contrato (V)", "Total del presupuesto", f"{f(pe['V'])} USD"],
        ["Costo variable (CV)", "Costo directo", f"{f(pe['CV'])} USD"],
        ["Costo fijo (CF)", "15 % x CV", f"{f(pe['CF'])} USD"],
        ["Utilidad (U)", "V - CV - CF", f"{f(pe['U'])} USD"],
        ["Margen de contribucion (m)", "(V - CV) / V", f"{f(pe['m'] * 100)} %"],
        ["Punto de equilibrio (PE)", "CF / m", f"{f(pe['PE'])} USD"],
        ["PE como fraccion del contrato", "PE / V", f"{f(pe['PE_pct'])} %"],
        [
            "Momento del plan",
            "Curva de inversion",
            f"{nombre_periodo(pe['periodo'])} (al {f(pe['fraccion_periodo'] * 100, 0)} % de ese dia)",
        ],
    ]
    flujo += [tabla(filas, [58 * mm, 48 * mm, ancho - 106 * mm], num_cols=(2,))]
    flujo += [Spacer(1, 3 * mm), g_equilibrio()]
    flujo += [
        Paragraph(
            f"<b>Lectura.</b> Hasta el {f(pe['PE_pct'])} % del contrato valuado ({f(pe['PE'])} USD), lo facturado solo cubre los costos. "
            f"Cada dolar valuado despues de ese punto deja {f(pe['m'] * 100)} centavos de margen, hasta la utilidad de {f(pe['U'])} USD al 100 %. "
            f"Segun el plan, el equilibrio llega durante el {nombre_periodo(pe['periodo'])}, cuando se entregan las laptops. "
            "Como las laptops concentran el valor, la fecha de entrega y la valuacion de los equipos deciden el flujo de caja del contratista, "
            "mas que la obra civil. Se recomienda pactar un anticipo o una valuacion parcial de suministros.",
            P,
        ),
        Paragraph(
            "El modelo supone que el costo fijo se causa completo. Si la administracion se causara proporcional al plazo, el equilibrio llegaria antes.",
            PS,
        ),
    ]

    # 10. Informe de auditoria -----------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("10. Informe de auditoria del presupuesto", H1)]
    flujo += [
        Paragraph(
            f"Resultado: <b>{'CUMPLE' if inf.cumple else 'NO CUMPLE'}</b> - {len(inf.hallazgos)} hallazgos ({n_graves} de severidad ERROR o CRITICO). El sistema genera este informe siempre, sin que se pida.",
            P,
        )
    ]
    filas = [["Regla", "Nombre", "Hallazgos", "Que comprueba en este caso"]]
    explica = {
        "R1": "Cada tramo EMT/UTP: cantidad = longitud x (1 + reserva) reevaluada",
        "R2": "La curva acumula exactamente el total del presupuesto",
        "R3": "Unidad del computo (m, pieza, punto) equivalente a la del APU",
        "R4": "Diametro, categoria, marca, puertos y capacidad presentes en el texto del APU",
        "R5": "Salidas = laptops + 2; certificaciones = salidas",
        "R6": "Cada equipo lleva el mismo factor de depreciacion en todos los APU",
        "R7": "Cada dia del plan concilia con el monto de sus partidas",
    }
    for codigo, nombre, n in inf.cuenta_por_regla_evaluada():
        filas.append([codigo, nombre, str(n), explica.get(codigo, "")])
    flujo += [tabla(filas, [13 * mm, 52 * mm, 18 * mm, ancho - 83 * mm], num_cols=(2,))]
    r4 = [h for h in inf.hallazgos if h.regla == "R4"]
    if r4:
        flujo += [
            Paragraph(
                f"<b>Los {len(r4)} avisos de R4 (INFO)</b> son todos de las claves 'origen' y 'destino' de los tramos. Son topologia, no atributos tecnicos, "
                "y por eso nunca aparecen en el texto del APU. No afectan el precio. Se registran como hallazgo del programa: el adaptador telecom "
                "deberia guardarlas como directivas (prefijo '_') para que R4 las ignore.",
                P,
            )
        ]

    flujo += [Paragraph("10.1 Pruebas de control de la auditoria (errores sembrados)", H2)]
    flujo += [
        Paragraph(
            "Para comprobar que la auditoria funciona en este caso, se siembra cada error conocido en una copia del presupuesto y se verifica que la regla que le corresponde lo detecta con severidad ERROR.",
            P,
        )
    ]
    filas = [["#", "Error sembrado", "Regla esperada", "Reglas que dispararon", "Resultado"]]
    extra = []
    for i, x in enumerate(controles, start=1):
        filas.append(
            [
                str(i),
                x["nombre"],
                ", ".join(x["esperado"]),
                ", ".join(x["detectadas"]) or "ninguna",
                "DETECTADO" if x["ok"] else "NO DETECTADO",
            ]
        )
        extra.append(("BACKGROUND", (4, i), (4, i), C_OK if x["ok"] else C_MAL))
    flujo += [tabla(filas, [7 * mm, 78 * mm, 22 * mm, 32 * mm, ancho - 139 * mm], extra=extra)]
    fallos = [x for x in controles if not x["ok"]]
    if fallos:
        flujo += [
            Paragraph(
                "<b>Por que se escapa el error sembrado en 1/2 pulg.</b> R4 da por buena una especificacion si su texto aparece "
                "como subcadena del texto del APU. El APU de TI-EMT1 cita la 'Dobladora de tubo EMT 1/2 a 1 1/2 pulg', y la cadena "
                "'1/2 pulg' esta dentro de '1 1/2 pulg'. Se reprodujo de forma aislada: una especificacion de 4 pulg contra un APU "
                "de 3/4 pulg (el caso inverso del hallazgo 5 de la linea base), una de 2 pulg contra 1/2 pulg y una de 6 pulg contra 16 pulg "
                "tampoco se detectan. El mismo error, sembrado con 3 pulg, si se detecta. Ver el hallazgo A-1 de la seccion 2.",
                P,
            )
        ]

    flujo += [Paragraph("10.2 Verificacion independiente del motor", H2)]
    flujo += [
        Paragraph(
            "El precio unitario de cada partida se recalculo linea por linea con la formula escrita de nuevo, sin llamar al motor, y se comparo con el resultado del motor.",
            P,
        )
    ]
    filas = [["Partida", "P.U. motor", "P.U. recalculado", "Diferencia"]]
    for codigo, mot, man, dif in sorted(verif, key=lambda x: orden.index(x[0])):
        filas.append([codigo, f(mot, 6), f(man, 6), f(dif, 6)])
    flujo += [tabla(filas, [30 * mm, 45 * mm, 45 * mm, 35 * mm], num_cols=(1, 2, 3))]

    flujo += [Paragraph("10.3 Sensibilidad del precio", H2)]
    filas = [["Escenario", "Total (USD)", "Variacion (USD)", "Variacion %"]]
    for n, tot, dv, pct in sens:
        filas.append([n, f(tot), f(dv), f(pct)])
    flujo += [tabla(filas, [95 * mm, 28 * mm, 28 * mm, ancho - 151 * mm], num_cols=(1, 2, 3))]
    flujo += [
        Paragraph(
            "<b>Lectura.</b> El precio es muy sensible al valor de las laptops y poco sensible a la estructura de mano de obra. "
            "Antes de emitir la oferta, conviene sustituir la referencia de categoria de MaPreX por una cotizacion fechada de HP "
            "(modelo, procesador, memoria y garantia) y declararla como fuente. El bono unico que exige el contrato de parametros "
            "sobrestima el precio en solo unos centavos por partida. Sumar administracion y utilidad en vez de encadenarlas "
            "subvaloraria la oferta en cerca de 1,2 %, y el motor lo impide por construccion.",
            P,
        )
    ]

    flujo += [Paragraph("10.4 Observaciones del auditor sobre el caso", H2)]
    for o in [
        "El switch de referencia (MaPreX ELC059) tiene puertos de acceso 10/100 y solo 2 puertos gigabit. Para un servidor y 12 puestos en Cat 6 conviene cotizar un switch gigabit en todos los puertos. El precio de referencia se mantiene y la especificacion se deja como observacion.",
        "Para 14 salidas bastaria un rack de 24U. Se adopto el de piso cerrado 42U de MaPreX porque es la unica referencia cerrada del listado, y el cerrado protege mejor al servidor. Con un rack abierto (ELC049) la partida TI-RACK bajaria cerca de 780 USD mas indirectos.",
        "Los rendimientos son estimados. Una vez ejecutada la obra deben sustituirse por rendimientos medidos, con referencia a la ejecucion.",
        "El FCAS de 600 % es el parametro por defecto del sistema y no tiene fuente normativa (decision D4). Aplicado al tecnico de redes, cuyo jornal no pertenece al tabulador de la construccion, sobrestima su costo. La sensibilidad muestra que el efecto es menor al 1 %.",
    ]:
        flujo += [Paragraph(f"- {o}", P)]

    doc = SimpleDocTemplate(
        str(salida),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="APU auditado TI-001 - Laptops HP, cableado y servidor en rack",
        author="Sistema de generacion y auditoria de APU",
    )
    doc.build(flujo, onFirstPage=pie, onLaterPages=pie)
    return salida


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", default=SALIDA_POR_DEFECTO, help="ruta del PDF")
    args = analizador.parse_args(argv)
    print(construir(Path(args.salida)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
