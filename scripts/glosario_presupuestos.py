"""Glosario de siglas y guía de fuentes para presupuestos (redes de computación), en PDF.

Acompaña el informe del caso TI-001 (`scripts/informe_ti001.py`): qué significa cada sigla del
informe y del sistema, de dónde sale cada dato de un presupuesto y una guía paso a paso para
presupuestar una red. Necesita el extra `informes` (reportlab).

Uso::

    uv run --extra informes python scripts/glosario_presupuestos.py --salida glosario.pdf
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SALIDA_POR_DEFECTO = "Glosario_y_fuentes_para_presupuestos.pdf"

C_CAB = colors.HexColor("#1f3b5c")
C_SUAVE = colors.HexColor("#eef3fa")
C_LINEA = colors.HexColor("#c9ced6")
GRIS = colors.HexColor("#52514e")

ss = getSampleStyleSheet()
H1 = ParagraphStyle(
    "H1", parent=ss["Heading1"], fontSize=15, textColor=C_CAB, spaceBefore=4, spaceAfter=6
)
H2 = ParagraphStyle(
    "H2", parent=ss["Heading2"], fontSize=11.5, textColor=C_CAB, spaceBefore=8, spaceAfter=4
)
P = ParagraphStyle("P", parent=ss["BodyText"], fontSize=8.8, leading=11.6, spaceAfter=4)
PS = ParagraphStyle("PS", parent=P, fontSize=7.6, leading=9.6, textColor=GRIS)
CEL = ParagraphStyle("CEL", parent=P, fontSize=7.6, leading=9.2, spaceAfter=0)
CELB = ParagraphStyle("CELB", parent=CEL, fontName="Helvetica-Bold")
CELW = ParagraphStyle("CELW", parent=CELB, textColor=colors.white)
ancho = A4[0] - 30 * mm


def tabla(filas, anchos):
    datos = [
        [Paragraph(str(x), CELW if i == 0 else (CELB if j == 0 else CEL)) for j, x in enumerate(f)]
        for i, f in enumerate(filas)
    ]
    t = Table(datos, colWidths=anchos, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), C_CAB),
        ("GRID", (0, 0), (-1, -1), 0.25, C_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for i in range(2, len(filas), 2):
        estilo.append(("BACKGROUND", (0, i), (-1, i), C_SUAVE))
    t.setStyle(TableStyle(estilo))
    return t


def glosario(titulo, filas, intro=None):
    bloque = [CondPageBreak(40 * mm), Paragraph(titulo, H2)]
    if intro:
        bloque.append(Paragraph(intro, P))
    bloque.append(
        tabla(
            [["Sigla / término", "Significado", "Para qué sirve en el presupuesto"]] + filas,
            [30 * mm, 62 * mm, ancho - 92 * mm],
        )
    )
    return bloque


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRIS)
    canvas.drawString(
        15 * mm,
        9 * mm,
        "Glosario de siglas y fuentes de información para presupuestos de redes y cómputo",
    )
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def construir(salida: Path) -> Path:
    """Arma el PDF en `salida` y devuelve la ruta."""
    flujo = []

    # Portada / cómo leer --------------------------------------------------------------------------
    flujo += [Spacer(1, 10 * mm)]
    flujo += [
        Paragraph(
            "Glosario de siglas y fuentes de información para presupuestos",
            ParagraphStyle("t", parent=H1, fontSize=20, leading=24),
        )
    ]
    flujo += [
        Paragraph(
            "Con aplicación a un presupuesto de redes de computación: caso TI-001, 12 laptops HP, cableado Cat 6, canalización EMT y servidor en rack",
            ParagraphStyle("t2", parent=H2, fontSize=12, leading=15, textColor=colors.black),
        )
    ]
    flujo += [Spacer(1, 4 * mm)]
    flujo += [
        Paragraph(
            "Este documento acompaña el informe del caso TI-001 (<i>scripts/informe_ti001.py</i>). Tiene tres partes: "
            "<b>(1)</b> qué significa cada sigla que aparece en el informe y en el sistema; <b>(2)</b> de dónde sale cada dato "
            "de un presupuesto y cómo se consigue; <b>(3)</b> una guía paso a paso para armar un presupuesto de redes de "
            "computación, con las reglas de cálculo de cantidades.",
            P,
        ),
        Paragraph(
            "Las siglas se agrupan por tema. Cuando una sigla es propia del proyecto de tesis (INV, GC, D4...), se indica. "
            "Donde un dato del caso TI-001 fue un supuesto y no una fuente, también se dice.",
            P,
        ),
    ]

    # 1. Glosario -------------------------------------------------------------------------------------
    flujo += [Paragraph("1. Glosario de siglas", H1)]

    flujo += glosario(
        "1.1 Costos y estructura del precio",
        [
            [
                "APU",
                "Análisis de Precio Unitario",
                "Desglose del costo de <b>una unidad</b> de una partida: materiales, equipos y mano de obra, más administración y utilidad.",
            ],
            [
                "PU",
                "Precio unitario",
                "Resultado del APU: lo que se cobra por cada unidad (m, pieza, punto). Precio total de la partida = cantidad × PU.",
            ],
            [
                "Partida",
                "Renglón del presupuesto",
                "Un trabajo con unidad propia; en TI-001, por ejemplo, TI-UTP es el cable en metros.",
            ],
            [
                "CD",
                "Costo directo",
                "Materiales + equipos + mano de obra de una partida. Es el costo variable del punto de equilibrio.",
            ],
            [
                "Adm.",
                "Administración (gastos generales)",
                "Porcentaje sobre el CD que cubre oficina, gerencia, seguros y fianzas. En TI-001, 15 %.",
            ],
            [
                "Util.",
                "Utilidad",
                "Ganancia del contratista, aplicada <b>en cascada</b> sobre CD + administración. En TI-001, 10 %: factor total 1,15 × 1,10 = 1,265.",
            ],
            [
                "FCAS",
                "Factor de Costos Asociados al Salario",
                "Multiplica el jornal para incluir prestaciones sociales, vacaciones, utilidades, aportes (IVSS, FAOV, INCES...) y beneficios contractuales. En el sistema es 6,00 (600 %).",
            ],
            [
                "Bono",
                "Bono de alimentación",
                "Monto diario por obrero a jornal que se suma aparte del FCAS. En TI-001, 5,81 USD/día (bono MaPreX del electricista N5).",
            ],
            [
                "Jornal",
                "Salario de un día de trabajo",
                "Base de la mano de obra a jornal: se divide entre el rendimiento.",
            ],
            [
                "Destajo",
                "Pago por unidad de obra (art. 114 LOTTT)",
                "La línea entra completa al PU, sin FCAS, sin bono y sin dividir entre rendimiento.",
            ],
            [
                "Rend.",
                "Rendimiento",
                "Unidades de la partida que ejecuta la cuadrilla en un día (m/día, puntos/día). Divide equipos y mano de obra.",
            ],
            [
                "Deprec. / Cop/Depr.",
                "Factor de depreciación (columna «Cop/Depr.» del listado de equipos MaPreX)",
                "Fracción del precio del equipo que se imputa por día de uso. 1,0 = precio de alquiler diario; 0,01 = 1 % del valor por día.",
            ],
            [
                "CF, CV, V, U, m",
                "Costo fijo, costo variable, venta, utilidad, margen de contribución",
                "Variables del punto de equilibrio: m = (V - CV) / V; PE = CF / m.",
            ],
            [
                "PE",
                "Punto de equilibrio",
                "Valuación acumulada a partir de la cual el contrato empieza a dejar ganancia. En TI-001: 28 586,76 USD (56,6 %).",
            ],
            [
                "Curva S / curva de inversión",
                "Monto acumulado del presupuesto período a período",
                "Muestra cuánto dinero se ejecuta cada día o semana; debe cerrar exactamente en el total.",
            ],
            [
                "Plan de trabajo",
                "Reparto de cada partida en el tiempo",
                "Fracción de cada partida que se ejecuta por período; alimenta la curva.",
            ],
            [
                "Valuación",
                "Cobro parcial por obra ejecutada",
                "Documento con el que el contratista factura el avance; la curva la anticipa.",
            ],
            [
                "Cómputos métricos",
                "Medición de las cantidades de obra",
                "Metros, piezas y puntos que salen de planos o levantamiento; son la «cantidad» del presupuesto.",
            ],
            [
                "USD, Bs",
                "Dólar estadounidense, bolívar",
                "Monedas del presupuesto y de las fuentes. MaPreX publica en Bs; el caso se convirtió a USD.",
            ],
            [
                "BCV",
                "Banco Central de Venezuela",
                "Publica la tasa oficial de cambio. En TI-001 se usó la tasa que declara el propio listado MaPreX: 633,3644 Bs/USD al 01/07/2026.",
            ],
            [
                "AACE",
                "Association for the Advancement of Cost Engineering (AACE International)",
                "Clasifica estimaciones por madurez. La tesis usa la clase 3 (presupuesto de control) como marco de contraste.",
            ],
        ],
    )

    flujo += glosario(
        "1.2 Fuentes, leyes y tabuladores (Venezuela)",
        [
            [
                "MaPreX",
                "Programa venezolano de análisis de precios y su base de precios",
                "Publica listados de materiales, equipos y mano de obra. Fuente de todos los precios de TI-001 (v26.0.0.1, julio 2026).",
            ],
            [
                "Ref (p. ej. ELA006)",
                "Código del insumo en el listado MaPreX",
                "Permite rastrear cada precio hasta su página del PDF. Aparece entre corchetes en cada línea de los APU.",
            ],
            [
                "CIV",
                "Colegio de Ingenieros de Venezuela",
                "Publica el tabulador de honorarios profesionales (escalafón P-1 a P-10) que MaPreX recoge.",
            ],
            [
                "P-1 ... P-10",
                "Escalafón profesional del tabulador CIV",
                "Nivel por años de experiencia; fija el honorario diario de ingenieros y arquitectos.",
            ],
            [
                "N2, N5, N7",
                "Niveles del tabulador de la construcción",
                "Categoría del obrero: N2 ayudante, N5 electricista de 1ra, N7 maestro electricista. Cada nivel tiene su jornal.",
            ],
            [
                "SAL CONST",
                "Salario de la construcción (agrupación del listado MaPreX)",
                "Tabulador de la convención colectiva de la construcción, con bono que completa 240 USD al mes.",
            ],
            [
                "TSU",
                "Técnico Superior Universitario",
                "Categoría del grupo «Profesionales-TSU» de MaPreX (p. ej. TSU en informática).",
            ],
            [
                "IVSS, FAOV, INCES",
                "Instituto Venezolano de los Seguros Sociales; Fondo de Ahorro Obligatorio para la Vivienda; Instituto Nacional de Capacitación y Educación Socialista",
                "Aportes patronales obligatorios que forman parte del FCAS.",
            ],
            [
                "LOTTT",
                "Ley Orgánica del Trabajo, los Trabajadores y las Trabajadoras (2012)",
                "Base legal de prestaciones, jornada y trabajo a destajo (art. 114).",
            ],
            [
                "COVENIN",
                "Comisión Venezolana de Normas Industriales",
                "Normas técnicas venezolanas; hoy administradas por FONDONORMA.",
            ],
            [
                "FONDONORMA",
                "Fondo para la Normalización y Certificación de la Calidad",
                "Organismo de normalización venezolano.",
            ],
            [
                "CEN",
                "Código Eléctrico Nacional (COVENIN / FONDONORMA 200)",
                "Reglas de instalaciones eléctricas y canalizaciones (tuberías EMT, ocupación de ductos, cajas).",
            ],
        ],
    )

    flujo += glosario(
        "1.3 Redes de computación y cableado estructurado",
        [
            [
                "UTP",
                "Unshielded Twisted Pair: par trenzado sin blindaje",
                "Cable de datos de 4 pares. Se presupuesta en metros.",
            ],
            [
                "Cat 6",
                "Categoría 6 (ANSI/TIA-568)",
                "Cable y conectores certificados hasta 250 MHz; soporta 1 Gbps a 100 m (10 Gbps en tramos cortos).",
            ],
            [
                "RJ45",
                "Registered Jack 45 (conector modular 8P8C)",
                "Conector de los cables de red: el macho va en el patch cord, el hembra (jack) en la salida.",
            ],
            ["Jack", "Conector hembra RJ45", "Se «poncha» en la salida de datos; uno por punto."],
            [
                "Face plate",
                "Placa frontal de la salida de datos",
                "Tapa del cajetín donde se monta el jack.",
            ],
            [
                "Cajetín 4×4",
                "Caja metálica de 4 × 4 pulg",
                "Caja empotrada o a la vista donde termina la tubería y se instala la salida.",
            ],
            [
                "Punto de red / salida",
                "Una toma de datos lista para usar",
                "Unidad «punto»: incluye cajetín, face plate y jack.",
            ],
            [
                "Patch panel",
                "Panel de parcheo",
                "Bloque de puertos en el rack donde terminan todos los cables horizontales (24 o 48 puertos).",
            ],
            [
                "Patch cord",
                "Cable corto con RJ45 en ambos extremos",
                "Conecta el patch panel al switch (0,5 m) y la laptop a la salida (2 m).",
            ],
            [
                "Switch",
                "Conmutador de red",
                "Equipo activo que interconecta los puntos. «48P» = 48 puertos; «10/100» = 100 Mbps por puerto; «Gigabit» = 1 000 Mbps.",
            ],
            [
                "Administrable",
                "Switch configurable (VLAN, monitoreo)",
                "Permite segmentar la red; conviene para oficinas con servidor.",
            ],
            [
                "PoE",
                "Power over Ethernet",
                "Alimentación eléctrica por el cable de datos (cámaras, puntos de acceso). No se usó en TI-001.",
            ],
            [
                "Rack 19 pulg",
                "Gabinete estándar de 19 pulgadas de ancho",
                "Donde se montan patch panel, switch, UPS y servidor.",
            ],
            [
                "U",
                "Unidad de rack (1,75 pulg = 44,45 mm de alto)",
                "Mide la altura de equipos y racks: 42U = 42 unidades.",
            ],
            [
                "Organizador horizontal",
                "Canal para ordenar patch cords en el rack",
                "Uno por cada patch panel o switch, como práctica.",
            ],
            [
                "Regleta / PDU",
                "Multitoma para rack (Power Distribution Unit)",
                "Distribuye energía a los equipos del rack.",
            ],
            [
                "UPS",
                "Uninterruptible Power Supply: sistema de alimentación ininterrumpida",
                "Respalda el rack ante cortes. Se dimensiona en VA.",
            ],
            ["VA", "Voltamperio", "Potencia aparente de la UPS (3 000 VA en TI-001)."],
            [
                "Servidor en rack",
                "Servidor de formato 1U/2U montado en el rack",
                "En TI-001: HP ProLiant o similar, referencia MaPreX OFI131.",
            ],
            [
                "i5 / i7",
                "Gamas de procesador Intel Core",
                "Referencias de categoría que usa MaPreX para laptops y servidores.",
            ],
            [
                "SO",
                "Sistema operativo",
                "Se instala y configura en el servidor y las laptops (partidas TI-SRV y TI-LAP).",
            ],
            [
                "Certificación",
                "Prueba del enlace con certificador",
                "Verifica que cada punto cumple Cat 6; un punto sin certificar no se recibe.",
            ],
            [
                "Enlace permanente",
                "Tramo fijo entre patch panel y salida",
                "Máximo 90 m según TIA-568; el canal completo, con patch cords, llega a 100 m.",
            ],
            [
                "ANSI / TIA",
                "American National Standards Institute / Telecommunications Industry Association",
                "Normas de cableado: TIA-568 (cableado), TIA-569 (canalizaciones y espacios), TIA-606 (etiquetado), TIA-607 (puesta a tierra).",
            ],
            [
                "ISO/IEC 11801",
                "Norma internacional de cableado genérico",
                "Equivalente internacional de TIA-568.",
            ],
            [
                "IEEE 802.3",
                "Norma de Ethernet",
                "Define velocidades y distancias de la red cableada.",
            ],
        ],
    )

    flujo += glosario(
        "1.4 Canalizaciones y material eléctrico",
        [
            [
                "EMT",
                "Electrical Metallic Tubing: tubería metálica eléctrica, de pared delgada",
                "Tubo de acero galvanizado a la vista o empotrado por donde van los cables. Se vende en tramos de 3 m.",
            ],
            [
                "IMC / RMC",
                "Intermediate / Rigid Metal Conduit",
                "Tuberías metálicas de pared intermedia o gruesa, para zonas expuestas a golpes o exteriores (no usadas en TI-001).",
            ],
            [
                "PVC",
                "Policloruro de vinilo",
                "Tubería plástica, rígida o corrugada, alternativa más barata a la EMT.",
            ],
            ["A.G.", "Acero galvanizado", "Recubrimiento de zinc contra la corrosión."],
            [
                "A.N. / A.B.",
                "Aguas negras / aguas blancas",
                "Clasificación de tuberías sanitarias en MaPreX (no eléctricas).",
            ],
            [
                'D=1"',
                "Diámetro nominal de 1 pulgada",
                'Las troncales de TI-001 son de 1"; las bajantes, de 3/4".',
            ],
            [
                "Anillo EMT",
                "Unión o acople entre tramos de EMT",
                "Uno por cada tramo de 3 m: 0,3333 por metro.",
            ],
            [
                "Conector EMT",
                "Pieza que fija el tubo a la caja",
                "Uno en cada llegada a caja o cajetín.",
            ],
            ["Curva EMT", "Codo de 90° prefabricado", "Uno por cada cambio de dirección."],
            [
                "Abrazadera",
                "Soporte que fija el tubo a pared o techo",
                "Una cada 1,5 a 3 m; en TI-001, 0,5 por metro.",
            ],
            [
                "Caja de paso",
                "Caja intermedia para halar cables",
                "Una cada 30 m aproximadamente o cada 2 curvas seguidas.",
            ],
            [
                "NEMA",
                "National Electrical Manufacturers Association",
                "Clasifica cajas por protección (NEMA 12: interior, contra polvo y goteo).",
            ],
            [
                "AWG / THW",
                "American Wire Gauge / aislamiento termoplástico resistente al calor y la humedad",
                "Calibre y aislamiento de cables eléctricos (no de datos).",
            ],
            [
                "Tirrap",
                "Amarre plástico (tie-wrap)",
                "Sujeta y ordena cables; se presupuesta por pieza.",
            ],
            [
                "Ocupación 40 %",
                "Porcentaje máximo de sección del tubo ocupado por cables",
                'Regla de TIA-569 y del CEN para más de dos cables: por eso las troncales de 6 cables Cat 6 son de 1" y no de 3/4".',
            ],
        ],
    )

    flujo += glosario(
        "1.5 Siglas del sistema de APU y de la tesis",
        [
            [
                "TI-001",
                "Código del presupuesto del caso de laptops HP",
                "TI = tecnología de información. Las partidas TI-EMT1, TI-EMT34, TI-PTO, TI-UTP, TI-CERT, TI-RACK, TI-UPS, TI-SW, TI-SRV y TI-LAP son sus renglones.",
            ],
            [
                "R1 ... R7",
                "Las siete reglas de verificación automática",
                "R1 trazabilidad de cantidades; R2 cierre de la curva; R3 coherencia de unidades; R4 especificaciones; R5 balance de cantidades; R6 depreciación; R7 conciliación del plan con el presupuesto.",
            ],
            [
                "INFO / ADVERTENCIA / ERROR / CRITICO",
                "Severidades de un hallazgo",
                "Con un solo ERROR o CRITICO el presupuesto «NO CUMPLE».",
            ],
            [
                "origen_id",
                "Identificador de la fuente de una cantidad",
                "Fila del CSV, elemento del modelo IFC, etc.: permite rastrear cada número.",
            ],
            [
                "BIM / BIM-5D",
                "Building Information Modeling; 5D = modelo 3D + tiempo + costo",
                "Marco de la tesis: cantidades derivadas del modelo y costeadas.",
            ],
            [
                "IFC",
                "Industry Foundation Classes (buildingSMART)",
                "Formato abierto de modelos BIM del que el adaptador civil extrae cantidades.",
            ],
            [
                "CSV / XLSX",
                "Valores separados por comas / libro de Excel",
                "Formatos de entrada (topología) y de salida (presupuesto exportado).",
            ],
            [
                "PF / IFPUG / HH",
                "Puntos de función / International Function Point Users Group / horas-hombre",
                "Medida y productividad del dominio «sistemas» (software).",
            ],
            [
                "ISBSG",
                "International Software Benchmarking Standards Group",
                "Fuente de productividad de referencia (HH por PF).",
            ],
            [
                "ML",
                "Aprendizaje automático (machine learning)",
                "Detección de precios atípicos y contraste con el mercado.",
            ],
            [
                "MAPE / RMSE / R²",
                "Error porcentual absoluto medio / raíz del error cuadrático medio / coeficiente de determinación",
                "Métricas del módulo predictivo.",
            ],
            [
                "ERS / RF / RNF / UC",
                "Especificación de Requisitos del Software / requisito funcional / no funcional / caso de uso",
                "Documentos de ingeniería de la tesis (IEEE 830).",
            ],
            [
                "ISO/IEC 25010",
                "Modelo de calidad del software",
                "Marco de los requisitos no funcionales.",
            ],
            [
                "API / UI",
                "Interfaz de programación / interfaz de usuario",
                "FastAPI y Streamlit en el sistema.",
            ],
            [
                "CI / PR",
                "Integración continua / pull request",
                "Pruebas automáticas en GitHub antes de fusionar cambios.",
            ],
            [
                "DRY",
                "Don't Repeat Yourself: «no te repitas»",
                "Principio de diseño: cada dato vive en un solo lugar.",
            ],
            [
                "G0, G1, G2 / GC0...GC6",
                "Compuertas del plan de desarrollo / del plan de cierre",
                "Hitos que no se cruzan sin cumplir su criterio (propio del proyecto).",
            ],
            [
                "INV-xxx",
                "Ítem del inventario de auditoría",
                "Registro numerado de defectos y deudas (propio del proyecto).",
            ],
            [
                "D4, D9",
                "Decisiones del dossier G0",
                "D4: el FCAS de 600 % no tiene fuente normativa; D9: modalidad jornal o destajo por línea.",
            ],
            [
                "NORMAS.md",
                "Documento de normas del proyecto",
                "Fuente única de la especificación del cálculo y de los contratos.",
            ],
        ],
    )

    # 2. Fuentes --------------------------------------------------------------------------------------
    flujo += [PageBreak(), Paragraph("2. De dónde sale cada dato de un presupuesto", H1)]
    flujo += [
        Paragraph(
            "Un presupuesto es tan confiable como su dato más débil. La regla práctica es que <b>cada número debe poder "
            "rastrearse</b> a un documento con fecha: plano, listado de precios, cotización, tabulador o ley. La tabla "
            "resume cada tipo de dato, dónde se consigue y cómo se usó en TI-001.",
            P,
        )
    ]
    fuentes = [
        ["Dato", "Fuente primaria", "Alternativas / contraste", "En TI-001", "Riesgo si falla"],
        [
            "Cantidades (m, piezas, puntos)",
            "Planos de arquitectura y levantamiento en sitio: ubicación de puestos, recorridos y alturas",
            "Modelo BIM (IFC), croquis acotado, lista de puestos del cliente",
            "Topología en CSV (zonas A, B y C; 14 puntos; longitudes por puesto). Supuesto del caso",
            "Es el error más caro: una cantidad mal medida se multiplica por el PU",
        ],
        [
            "Precio de materiales",
            "Listados de precios publicados (MaPreX) con fecha y código",
            "Tres cotizaciones de proveedores locales; catálogos de fabricantes",
            "MaPreX materiales.pdf, 09/07/2026, con su Ref por insumo",
            "Precios vencidos; inflación; producto no equivalente",
        ],
        [
            "Equipos de TI (laptops, servidor, switch, UPS)",
            "Cotización formal del fabricante o distribuidor (modelo, memoria, garantía)",
            "Referencias de categoría del listado (MaPreX OFI058, OFI131)",
            "Referencias de categoría MaPreX. <b>No es cotización de HP</b>",
            "Alto: las laptops son el 72 % del total",
        ],
        [
            "Herramientas y equipos de instalación",
            "Listado de equipos con factor de depreciación (MaPreX equipos.pdf)",
            "Cálculo propio: valor / vida útil en días; tarifas de alquiler",
            "MaPreX: precio × factor Cop/Depr.",
            "Bajo en redes: pesan poco",
        ],
        [
            "Jornal de obreros",
            "Tabulador de la convención colectiva de la construcción (niveles N1-N9)",
            "Tabuladores sectoriales (petrolero, PEQUIVEN) según el cliente",
            "MaPreX mano_de_obra.pdf, 01/07/2026 (N2, N5, N7) y técnico de redes",
            "Usar un tabulador que no aplica a la obra",
        ],
        [
            "Honorarios profesionales",
            "Tabulador del CIV (P-1 a P-10)",
            "Tarifas de mercado de TI; contratos previos",
            "No se usaron en APU: la supervisión entra en administración",
            "Doble cómputo si se ponen en APU y en administración",
        ],
        [
            "FCAS y bono",
            "Cálculo desde la LOTTT, la convención colectiva y los aportes legales vigentes",
            "Porcentajes publicados por programas de APU o cámaras del sector",
            "FCAS 600 % (parámetro del sistema, sin fuente normativa: D4); bono MaPreX 5,81 USD",
            "Medio: en TI-001 bajar el FCAS a 300 % cambia el total -0,85 %",
        ],
        [
            "Rendimientos",
            "Rendimientos medidos en obras propias (históricos)",
            "Manuales de rendimientos, experiencia del maestro de obra, fabricantes",
            "Estimados y declarados (p. ej. 150 m/día de UTP, 8 puntos/día)",
            "Subestimar el tiempo encarece la mano de obra real",
        ],
        [
            "Tasa de cambio",
            "BCV, tasa oficial del día del presupuesto",
            "Tasa declarada en la fuente de precios",
            "633,3644 Bs/USD (la del listado MaPreX, 01/07/2026)",
            "Mezclar precios convertidos con tasas de días distintos",
        ],
        [
            "Administración y utilidad",
            "Política de la empresa; estructura de gastos de oficina",
            "Pliegos de licitación; práctica del sector (10-20 % y 10-15 %)",
            "15 % y 10 % en cascada",
            "Sumar en vez de encadenar: -1,19 % en TI-001",
        ],
        [
            "Criterios técnicos",
            "Normas: TIA-568, TIA-569, TIA-606, CEN (COVENIN 200), ISO/IEC 11801",
            "Guías de fabricantes de cableado",
            'Ocupación 40 % (troncal 1"), enlace de 90 m como máximo, certificación y etiquetado',
            "Instalación que no pasa la certificación: se rehace",
        ],
    ]
    flujo += [tabla(fuentes, [27 * mm, 38 * mm, 36 * mm, 42 * mm, ancho - 143 * mm])]
    flujo += [Spacer(1, 3 * mm)]
    flujo += [Paragraph("2.1 Cómo leer y usar los listados MaPreX", H2)]
    for t in [
        "<b>Tres archivos</b> en <i>data/precios/maprex_2026-07/</i>: <i>materiales.pdf</i> (Ref, descripción, unidad, precio, proveedor), "
        "<i>equipos.pdf</i> (precio o alquiler, factor Cop/Depr. y total por día) y <i>mano_de_obra.pdf</i> (jornal, bono, agrupación o tabulador y nivel).",
        "<b>Todo está en bolívares.</b> Para pasar a USD se divide entre la tasa declarada en el listado (633,3644 Bs/USD al 01/07/2026). "
        "Ejemplo: cable UTP Cat 6, Ref ELA006, 1 510,00 Bs/m ÷ 633,3644 = 2,3841 USD/m.",
        '<b>Se busca el insumo equivalente</b> por descripción (p. ej. «TUBO EMT D=1"») y se anota su Ref. Si hay varios proveedores con precios distintos, '
        "se elige uno y se declara el criterio: el más reciente, el promedio o el del proveedor de la zona.",
        "<b>Los equipos de TI aparecen en equipos.pdf</b> con precio de adquisición. Cuando se <b>entregan al cliente</b> (laptops, servidor), entran al APU "
        "como material con el precio completo. Cuando son <b>herramienta del instalador</b> (certificador, laptop de configuración), entran como equipo con su factor.",
        "<b>Limitación:</b> MaPreX da referencias de categoría («laptop i7 o similar»), no marcas ni modelos. Para una oferta real hay que sustituirlas por cotizaciones fechadas.",
    ]:
        flujo += [Paragraph(f"- {t}", P)]

    flujo += [
        CondPageBreak(70 * mm),
        Paragraph("2.2 Dónde está cada fuente dentro del repositorio", H2),
    ]
    flujo += [
        tabla(
            [
                ["Qué", "Ruta"],
                [
                    "Listados MaPreX originales (PDF)",
                    "data/precios/maprex_2026-07/materiales.pdf, equipos.pdf, mano_de_obra.pdf",
                ],
                [
                    "Referencias ya convertidas a USD por dominio",
                    "data/precios/maprex_2026-07/referencia_telecom.csv, referencia_sistemas.csv, lista_maprex_usd.csv",
                ],
                [
                    "Plantillas de precios por dominio",
                    "data/telecom/plantilla_precios.csv, data/sistemas/plantilla_precios.csv",
                ],
                [
                    "Leyes y fuentes normativas",
                    "docs/fuentes/ (LOTTT, estudios sobre el FCAS y su ficha en docs/fuentes/README.md)",
                ],
                ["Protocolo para recolectar precios", "docs/protocolo_precios.md"],
                ["Fórmula del cálculo y parámetros", "NORMAS.md §4"],
                [
                    "Caso TI-001 (topología, scripts, PDF y Excel)",
                    "Escritorio/APU_Laptops_HP_Rack/ (fuera del repositorio)",
                ],
            ],
            [70 * mm, ancho - 70 * mm],
        )
    ]

    # 3. Guía redes --------------------------------------------------------------------------------------
    flujo += [
        PageBreak(),
        Paragraph("3. Guía para armar un presupuesto de redes de computación", H1),
    ]
    flujo += [
        Paragraph(
            "Paso a paso, con las reglas de cantidades que se usaron en TI-001. Cada paso indica qué información hace falta y de dónde sale.",
            P,
        )
    ]
    pasos = [
        (
            "1. Levantar el alcance",
            "Cuántos puestos hay (laptops o PC), dónde están, qué otros equipos van a la red (impresoras, puntos de acceso, cámaras), dónde irá el cuarto técnico o rack y qué equipos activos se piden (switch, servidor, UPS). <b>Fuente:</b> el cliente y una visita al sitio con plano o croquis acotado.",
        ),
        (
            "2. Definir los puntos de red",
            "Puntos = puestos + equipos de red + reserva (10-20 %). En TI-001: 12 laptops + impresora + 1 reserva = 14. El sistema lo verifica con R5 mediante el balance <i>{TI-LAP} + 2</i>.",
        ),
        (
            "3. Medir cada recorrido de cable",
            "Por cada punto: distancia del rack a la salida siguiendo la ruta real de la tubería (subidas y bajadas incluidas). Longitud a presupuestar = distancia × (1 + reserva), con reserva de 10 % para curvas y holgura en los extremos. <b>Límite:</b> ningún enlace permanente debe superar 90 m (TIA-568). En TI-001, 341 m medidos × 1,10 = 375,1 m.",
        ),
        (
            "4. Diseñar las canalizaciones",
            'Troncales desde el rack hasta cada zona y bajantes hasta cada salida. El diámetro sale de la ocupación máxima del 40 %: como guía, por 3/4" pasan unos 3 o 4 cables Cat 6 y por 1" unos 6 a 8. Verificar con el diámetro exterior del cable del fabricante. Accesorios por metro: anillo 1/3 (tramos de 3 m), abrazadera 0,5, curva por cada cambio de dirección, conector por llegada a caja y caja de paso cada 30 m.',
        ),
        (
            "5. Equipos del rack",
            "Patch panel: número de puntos ÷ 24, redondeado hacia arriba. Switch: puertos al menos iguales a puntos + servidor + enlaces de subida. Altura del rack: suma de las U de cada equipo + 30-50 % de crecimiento. UPS: suma de la potencia de los equipos del rack con margen (25 % o más) y la autonomía que pida el cliente.",
        ),
        (
            "6. Equipos de usuario y servidor",
            "Modelo, procesador, memoria, disco, garantía y licencias (sistema operativo, antivirus, ofimática). <b>Fuente:</b> cotización formal fechada del distribuidor; el listado MaPreX sirve como referencia de contraste.",
        ),
        (
            "7. Certificación y documentación",
            "Una certificación por punto, etiquetado en los dos extremos (TIA-606) y entrega de planos como construidos y reporte del certificador. Se presupuesta por punto.",
        ),
        (
            "8. Componer cada APU",
            "Materiales por unidad (no se dividen entre el rendimiento), equipos con su factor, cuadrilla con su jornal y el rendimiento diario. Fórmula: PU = [materiales + (equipos + mano de obra con FCAS y bono) / rendimiento] × 1,15 × 1,10.",
        ),
        (
            "9. Plan y curva",
            "Repartir cada partida por días según las cuadrillas disponibles (en TI-001: cuadrilla eléctrica y técnico de redes en paralelo). La certificación va al final porque necesita el cableado terminado.",
        ),
        (
            "10. Auditar",
            "Correr las siete reglas del sistema. Revisar además, a mano, que los precios de los equipos de TI sean cotizaciones vigentes, que ningún enlace pase de 90 m y que la curva cierre en el total. Hacer un análisis de sensibilidad sobre los insumos que más pesan.",
        ),
    ]
    flujo += [
        tabla(
            [["Paso", "Qué se hace y de dónde sale la información"]] + [list(p) for p in pasos],
            [38 * mm, ancho - 38 * mm],
        )
    ]
    flujo += [Spacer(1, 3 * mm), Paragraph("3.1 Partidas típicas de un presupuesto de redes", H2)]
    flujo += [
        tabla(
            [
                ["Partida", "Unidad", "Regla de cantidad", "Insumos principales"],
                [
                    "Canalización EMT (troncal / bajante)",
                    "m",
                    "Suma de tramos × (1 + 5 %)",
                    "Tubo, anillos, conectores, curvas, abrazaderas y cajas de paso",
                ],
                [
                    "Salida de datos",
                    "punto",
                    "Puestos + equipos + reserva",
                    "Cajetín, face plate y jack Cat 6",
                ],
                ["Cable UTP Cat 6", "m", "Suma de recorridos × (1 + 10 %)", "Cable y tirraps"],
                [
                    "Certificación y etiquetado",
                    "punto",
                    "Igual a las salidas",
                    "Patch cord de 0,5 m y etiquetas; certificador",
                ],
                [
                    "Rack con accesorios",
                    "pieza",
                    "1 por cuarto técnico",
                    "Rack, patch panel, organizador, regleta y bandeja",
                ],
                [
                    "Switch",
                    "pieza",
                    "Puertos requeridos ÷ puertos por equipo",
                    "Switch y patch cords",
                ],
                ["UPS", "pieza", "Según carga y autonomía", "UPS de rack"],
                [
                    "Servidor",
                    "pieza",
                    "Según la necesidad del cliente",
                    "Servidor, patch cords y licencias",
                ],
                [
                    "Estaciones (laptops / PC)",
                    "pieza",
                    "Número de usuarios",
                    "Equipo y patch cord de 2 m; configuración",
                ],
            ],
            [44 * mm, 15 * mm, 46 * mm, ancho - 105 * mm],
        )
    ]
    flujo += [Spacer(1, 3 * mm)]
    flujo += [Paragraph("3.2 Lista de verificación antes de entregar", H2)]
    for t in [
        "Cada precio tiene fuente, código o Ref y fecha; los equipos de TI tienen cotización vigente.",
        "Todas las conversiones Bs/USD usan la misma tasa, declarada con su fecha.",
        "La cantidad de salidas coincide con la de certificaciones, patch cords y puertos del patch panel.",
        "Ningún enlace supera 90 m y ninguna tubería pasa del 40 % de ocupación.",
        "Administración y utilidad van en cascada; los materiales no se dividen entre el rendimiento.",
        "La curva cierra exactamente en el total y cada período concilia con sus partidas (R2 y R7).",
        "El informe declara los supuestos: rendimientos estimados, referencias de categoría y FCAS.",
    ]:
        flujo += [Paragraph(f"- {t}", P)]
    flujo += [
        Spacer(1, 4 * mm),
        Paragraph(
            "Nota: las cifras de TI-001 son de un caso construido con fines académicos. Los precios son referencias publicadas "
            "(MaPreX, julio de 2026), no cotizaciones de una obra real.",
            PS,
        ),
    ]

    doc = SimpleDocTemplate(
        str(salida),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Glosario y fuentes para presupuestos",
        author="Sistema de generación y auditoría de APU",
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
