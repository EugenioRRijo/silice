"""Línea base auditada: los cinco APU del caso didáctico, con su cómputo, presupuesto y curva.

Única copia de estos datos en el sistema (CLAUDE.md §2, principio DRY).
Fuente primaria: data/linea_base/APUS_CLINICA.pdf (presupuesto 001, 28/04/2026, USD).
Versión narrativa: docs/linea_base.md.

Consumidores: tests/unit/test_costing.py, tests/unit/test_linea_base.py, scripts/seed.py
(Sesión I0.4) y la fixture de las siete inconsistencias de la Sesión I4.

Los códigos de partida llevan el prefijo LB- (línea base) porque los códigos COVENIN 2000
definitivos se asignan al cargar el catálogo en la Sesión I0.4; ninguna prueba debe depender de
un código no verificado contra la norma.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from core.contracts import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
    PuntoCurva,
)

FECHA_LINEA_BASE = date(2026, 4, 28)
MONEDA = "USD"
CODIGO_PRESUPUESTO = "001"

# Parámetros de la estructura de costos del caso: los valores por defecto del contrato SON los de la
# línea base (FCAS 600 %, bono 1,00, administración 15 %, utilidad 10 %). No se repiten aquí.
PARAMETROS_LINEA_BASE = ParametrosCosto()


def _mat(descripcion: str, unidad: str, cantidad: str, precio: str) -> LineaMaterial:
    return LineaMaterial(descripcion, unidad, Decimal(cantidad), Decimal(precio))


def _eq(descripcion: str, cantidad: str, precio: str, depreciacion: str) -> LineaEquipo:
    return LineaEquipo(descripcion, Decimal(cantidad), Decimal(precio), Decimal(depreciacion))


def _mo(descripcion: str, cantidad: str, sueldo: str) -> LineaManoObra:
    return LineaManoObra(descripcion, Decimal(cantidad), Decimal(sueldo))


# ---------------------------------------------------------------------------------------------
# Los cinco APU, transcritos línea a línea del PDF. Las descripciones de equipos del encofrado
# siguen el orden del PDF; los importes son exactos en todos los casos.
# ---------------------------------------------------------------------------------------------

APU_EXCAVACION = ComposicionAPU(
    codigo_partida="LB-01-EXC",
    descripcion="Excavación en tierra para zanja de tubería y fosos de tanquillas",
    unidad="m3",
    rendimiento=Decimal("80"),
    equipos=(
        _eq("Retroexcavadora", "1", "200", "1.00"),
        _eq("Pico", "2", "25", "0.03"),
        _eq("Pala", "2", "15", "0.03"),
        _eq("Camión de volteo", "1", "150", "1.00"),
        _eq("Vehículo de transporte", "1", "50", "1.00"),
    ),
    mano_obra=(
        _mo("Operador de equipo de 1ra", "1", "5"),
        _mo("Ayudante", "2", "3"),
        _mo("Chofer de 2da", "1", "5"),
        _mo("Chofer de 4ta", "1", "3.5"),
    ),
)

APU_TUBERIA = ComposicionAPU(
    codigo_partida="LB-02-TUB",
    descripcion="Suministro e instalación de tubería PVC de 4 pulgadas",
    unidad="pieza",  # el cómputo la mide en "mts": hallazgo 4
    rendimiento=Decimal("100"),
    materiales=(
        _mat("Tubería PVC 4 pulg", "m", "1.05", "6"),
        _mat("Curva PVC 4 pulg", "unidad", "0.2", "2.5"),
        _mat("Conector PVC 4 pulg", "unidad", "0.2", "1.2"),
        _mat("Pegamento para PVC", "unidad", "0.01", "15"),
    ),
    equipos=(
        _eq("Segueta", "2", "15", "0.03"),
        _eq("Cinta métrica", "2", "15", "0.03"),
        # depreciación 0,03 aquí y 1,00 en los otros cuatro APU: hallazgo 7
        _eq("Vehículo de transporte", "1", "50", "0.03"),
    ),
    mano_obra=(
        _mo("Maestro (electricista, según el APU original)", "1", "5"),
        _mo("Ayudante", "1", "3"),
        _mo("Chofer de 4ta", "1", "3.5"),
    ),
)

APU_ENCOFRADO = ComposicionAPU(
    codigo_partida="LB-03-ENC",
    descripcion="Encofrado recto de madera para paredes de tanquillas",
    unidad="m2",
    rendimiento=Decimal("16"),
    materiales=(
        _mat("Madera", "m2", "1.1", "12"),
        _mat("Listones de madera 2x2", "m2", "0.5", "3"),
        _mat("Clavos de acero 2 1/2 pulg", "unidad", "0.2", "2.5"),
        _mat("Desencofrante", "unidad", "0.1", "4"),
    ),
    equipos=(
        _eq("Sierra circular eléctrica", "1", "100", "0.03"),
        _eq("Martillo", "2", "15", "0.03"),
        _eq("Nivel de mano", "2", "10", "0.03"),
        _eq("Cinta métrica", "2", "160", "0.03"),
        _eq("Alicate", "2", "20", "0.03"),
        _eq("Vehículo de transporte", "1", "50", "1.00"),
    ),
    mano_obra=(
        _mo("Carpintero de 1ra", "1", "5"),
        _mo("Ayudante", "2", "3"),
        _mo("Chofer de 4ta", "1", "3.5"),
    ),
)

APU_CONCRETO = ComposicionAPU(
    codigo_partida="LB-04-CON",
    descripcion="Vaciado de concreto en paredes de tanquillas",
    unidad="m3",
    rendimiento=Decimal("8"),
    materiales=(
        _mat("Cemento Portland", "saco", "7.5", "15"),  # el PDF dice "unidad"
        _mat("Arena lavada", "m3", "0.45", "30"),
        _mat("Piedra picada", "m3", "0.8", "35"),
        _mat("Agua", "m3", "0.2", "12"),
    ),
    equipos=(
        _eq("Mezcladora de concreto", "1", "60", "1.00"),
        _eq("Vibrador de concreto", "1", "20", "1.00"),
        _eq("Carretilla", "2", "30", "0.03"),
        _eq("Nivel de mano", "1", "40", "0.03"),
        _eq("Pala", "2", "10", "0.03"),
        _eq("Tobos plásticos", "2", "3", "0.03"),
        _eq("Vehículo de transporte", "1", "50", "1.00"),
    ),
    mano_obra=(
        _mo("Albañil de 1ra", "1", "5"),
        _mo("Ayudante", "4", "3"),
        _mo("Chofer de 4ta", "1", "3.5"),
    ),
)

APU_RELLENO = ComposicionAPU(
    codigo_partida="LB-05-REL",
    descripcion="Relleno compactado con material granular",
    unidad="m3",
    rendimiento=Decimal("8"),
    materiales=(
        _mat("Material granular", "m3", "1.15", "12"),  # el PDF dice "unidad"
        _mat("Agua", "m3", "0.1", "2"),
    ),
    equipos=(
        _eq("Compactadora de percusión tipo sapo", "1", "20", "1.00"),
        _eq("Herramientas menores", "1", "1", "1.00"),
        _eq("Vehículo de transporte", "1", "50", "1.00"),
    ),
    mano_obra=(
        _mo("Albañil de 1ra", "1", "5"),
        _mo("Ayudante", "4", "3"),
        _mo("Chofer de 4ta", "1", "3.5"),
    ),
)

APUS_LINEA_BASE = (APU_EXCAVACION, APU_TUBERIA, APU_ENCOFRADO, APU_CONCRETO, APU_RELLENO)

# Precio unitario que muestra el PDF para cada APU ("Total Final"). Tolerancia de prueba: ± 0,01.
PRECIO_UNITARIO_ESPERADO = {
    "LB-01-EXC": Decimal("8.60"),
    "LB-02-TUB": Decimal("10.19"),
    "LB-03-ENC": Decimal("33.24"),
    "LB-04-CON": Decimal("242.64"),
    "LB-05-REL": Decimal("52.58"),
}

# Subtotales que muestra el PDF, para localizar en qué paso falla el motor si un PU no coincide.
# materiales: Σ cantidad × precio (entra completo, sin dividir entre rendimiento)
# equipos_total: Σ cantidad × precio × depreciación, ANTES de dividir entre rendimiento
# sueldos: Σ cantidad × sueldo, antes de prestaciones y bono
# obreros: Σ cantidad de mano de obra (base del bono de alimentación)
# costo_directo: materiales + equipos/rend + mano de obra/rend, redondeado como en el PDF
SUBTOTALES_ESPERADOS = {
    "LB-01-EXC": {
        "materiales": Decimal("0.00"),
        "equipos_total": Decimal("402.40"),
        "sueldos": Decimal("19.50"),
        "obreros": Decimal("5"),
        "costo_directo": Decimal("6.80"),
    },
    "LB-02-TUB": {
        "materiales": Decimal("7.19"),
        "equipos_total": Decimal("3.30"),
        "sueldos": Decimal("11.50"),
        "obreros": Decimal("3"),
        "costo_directo": Decimal("8.06"),
    },
    "LB-03-ENC": {
        "materiales": Decimal("15.60"),
        "equipos_total": Decimal("65.30"),
        "sueldos": Decimal("14.50"),
        "obreros": Decimal("4"),
        "costo_directo": Decimal("26.28"),
    },
    "LB-04-CON": {
        "materiales": Decimal("156.40"),
        "equipos_total": Decimal("133.78"),
        "sueldos": Decimal("20.50"),
        "obreros": Decimal("6"),
        "costo_directo": Decimal("191.81"),
    },
    "LB-05-REL": {
        "materiales": Decimal("14.00"),
        "equipos_total": Decimal("71.00"),
        "sueldos": Decimal("20.50"),
        "obreros": Decimal("6"),
        "costo_directo": Decimal("41.56"),
    },
}

# ---------------------------------------------------------------------------------------------
# Geometría del caso y memoria de cálculo (hoja "Cómputos métricos" del PDF)
# ---------------------------------------------------------------------------------------------

GEOMETRIA_TANQUILLA = {
    "a": Decimal("0.80"),  # ancho exterior, m
    "h": Decimal("0.80"),  # altura, m
    "e": Decimal("0.10"),  # espesor de pared, m
}
N_TANQUILLAS = Decimal("4")
TRAMOS_TUBERIA_M = (Decimal("8.00"), Decimal("3.00"), Decimal("8.00"), Decimal("5.00"))
LONGITUD_TUBERIA_M = Decimal("24.00")
DIAMETRO_TUBERIA_PROYECTO = "4 pulg"
DIAMETRO_TUBERIA_MEMORIA = "3/4 pulg"  # error de transcripción: hallazgo 5
ZANJA = {"ancho": Decimal("0.40"), "profundidad": Decimal("0.80"), "volumen": Decimal("7.68")}
# 4 × 0,515 = 2,06 m3; sumado a la zanja da los 9,74 m3 del presupuesto
VOLUMEN_FOSO_TANQUILLA = Decimal("0.515")

# Por tanquilla: lo que la memoria calcula vs lo que el cómputo multiplicó (hallazgos 1 y 2)
CANTIDAD_POR_TANQUILLA_MEMORIA = {"LB-03-ENC": Decimal("4.48"), "LB-04-CON": Decimal("0.224")}
CANTIDAD_POR_TANQUILLA_USADA = {"LB-03-ENC": Decimal("5.92"), "LB-04-CON": Decimal("0.415")}

# Cómputo corregido a partir de la memoria. El resto de partidas se corrige con las reglas
# paramétricas de la Sesión I3.2 (sobreancho y espesor de fondo aún por definir).
COMPUTO_CORREGIDO = {"LB-03-ENC": Decimal("17.92"), "LB-04-CON": Decimal("0.896")}

# ---------------------------------------------------------------------------------------------
# Presupuesto y curva tal como fueron emitidos (hojas "Presupuesto" y "Plan de trabajo")
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LineaPresupuestoAuditado:
    codigo_partida: str
    descripcion_computo: str
    unidad_computo: str  # la que escribió el proyectista; puede no coincidir con la del APU
    cantidad: Decimal
    precio_unitario: Decimal
    total: Decimal


PRESUPUESTO_AUDITADO = (
    LineaPresupuestoAuditado(
        "LB-01-EXC", "Excavación", "m3", Decimal("9.74"), Decimal("8.60"), Decimal("83.77")
    ),
    LineaPresupuestoAuditado(
        "LB-02-TUB", "Tubería de 4 pulg", "mts", Decimal("24"), Decimal("10.19"), Decimal("244.64")
    ),
    LineaPresupuestoAuditado(
        "LB-03-ENC", "Encofrado", "m3", Decimal("23.68"), Decimal("33.24"), Decimal("787.07")
    ),
    LineaPresupuestoAuditado(
        "LB-04-CON",
        "Vaciado de concreto",
        "m3",
        Decimal("1.66"),
        Decimal("242.64"),
        Decimal("402.78"),
    ),
    LineaPresupuestoAuditado(
        "LB-05-REL", "Relleno", "m3", Decimal("1.3"), Decimal("52.58"), Decimal("68.35")
    ),
)
TOTAL_PRESUPUESTO_AUDITADO = Decimal("1586.61")

CURVA_AUDITADA = (
    PuntoCurva("Día 1 Excavación", Decimal("82.98"), Decimal("82.98")),
    PuntoCurva("Día 2 Tubería de 4 pulg", Decimal("244.56"), Decimal("327.54")),
    PuntoCurva("Día 3 Encofrado inicio", Decimal("389.77"), Decimal("717.31")),
    PuntoCurva("Día 4 Encofrado cierre", Decimal("389.78"), Decimal("1107.09")),
    PuntoCurva("Día 5 Vaciado de concreto", Decimal("401.21"), Decimal("1508.30")),
    PuntoCurva("Día 6 Relleno", Decimal("67.20"), Decimal("1575.50")),
)
TOTAL_CURVA_AUDITADA = Decimal("1575.50")
PORCENTAJE_CIERRE_CURVA = Decimal("99.30")

# ---------------------------------------------------------------------------------------------
# Las siete inconsistencias documentadas (Bases del anteproyecto §2.2) y la regla que las detecta
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Inconsistencia:
    numero: int
    titulo: str
    codigo_partida: str | None
    observado: str
    esperado: str
    regla: str
    evidencia: str


INCONSISTENCIAS = (
    Inconsistencia(
        1,
        "Encofrado",
        "LB-03-ENC",
        "5,92 m2 por tanquilla (23,68 m2 en total)",
        "4,48 m2 por tanquilla según la memoria (17,92 m2 en total)",
        "R1",
        "La memoria detalla 1,92 + 2,56 = 4,48 m2 pero el cómputo multiplica por 5,92. "
        "Sobreestimación del 32 %; el origen de 5,92 no está justificado.",
    ),
    Inconsistencia(
        2,
        "Concreto",
        "LB-04-CON",
        "0,415 m3 por tanquilla (1,66 m3 en total)",
        "0,224 m3 por tanquilla según la memoria (0,896 m3 en total)",
        "R1",
        "La memoria calcula 0,28 m2 × 0,80 m = 0,224 m3 pero el cómputo aplica 0,415. "
        "Sobreestimación del 85 % en la partida de mayor costo unitario (242,64 USD/m3).",
    ),
    Inconsistencia(
        3,
        "Curva de inversión",
        None,
        "1 575,50 USD acumulados (99,30 %)",
        "1 586,61 USD, el total del presupuesto",
        "R2",
        "El gasto acumulado del plan de trabajo no cierra al 100 %. "
        "Diferencia no conciliada de 11,11 USD.",
    ),
    Inconsistencia(
        4,
        "Unidades",
        "LB-02-TUB",
        'cómputo en "mts" (24 m)',
        'APU definido en "Pieza"',
        "R3",
        "Incompatibilidad dimensional entre el APU y el cómputo que lo consume.",
    ),
    Inconsistencia(
        5,
        "Diámetro",
        "LB-02-TUB",
        "3/4 pulg en la memoria de cómputo",
        "4 pulg en el sistema proyectado y en el APU",
        "R4",
        "Error de transcripción que sobrevive por ausencia de validación cruzada.",
    ),
    Inconsistencia(
        6,
        "Relleno",
        "LB-05-REL",
        "1,30 m3 rellenados",
        "excavación − concreto − tubería ≈ 8,6 m3 (con el concreto corregido)",
        "R5",
        "Se excavan 9,74 m3 y se rellenan 1,30 m3 sin que la diferencia esté justificada por "
        "concreto, tubería ni transporte de material sobrante.",
    ),
    Inconsistencia(
        7,
        "Depreciación",
        "LB-02-TUB",
        "vehículo de transporte con factor 0,03 en tubería y 1,00 en los otros cuatro APU",
        "un solo factor por insumo, con criterio de amortización declarado",
        "R6",
        "Regla de imputación de equipos no documentada ni reproducible.",
    ),
)

# Hallazgos adicionales detectados al transcribir el PDF en el Sprint 0. No forman parte de las
# siete inconsistencias de la línea base (no se cuentan en el indicador 1), pero las reglas
# también los cubren.
HALLAZGOS_ADICIONALES = (
    Inconsistencia(
        8,
        "Unidad del encofrado",
        "LB-03-ENC",
        'cómputo y presupuesto en "m3"',
        'APU definido en "m2"',
        "R3",
        "Segunda incompatibilidad dimensional, no listada en las Bases del anteproyecto.",
    ),
    Inconsistencia(
        9,
        "Plan de trabajo vs presupuesto",
        None,
        "día 1 = 82,98; días 3+4 = 779,55; día 5 = 401,21; día 6 = 67,20",
        "83,77; 787,07; 402,78; 68,35 (los montos de las partidas)",
        "R7",
        "Cada monto diario es menor que el de su partida; explica la brecha de 11,11 USD "
        "del hallazgo 3.",
    ),
)
