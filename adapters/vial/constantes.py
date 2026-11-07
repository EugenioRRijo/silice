"""Constantes y partidas de la especialidad vial, cada una con su fuente o «supuesto declarado».

`Constante` es una copia deliberada de la de `adapters/espacio/especialidades/__init__.py`: un
adaptador no importa de otro (NORMAS.md §2; `tests/unit/test_arquitectura.py`), así que lo que se
necesita igual se duplica y se declara aquí.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

#: Fuente de toda constante cuya fuente normativa no está verificada (misma etiqueta que espacio).
SUPUESTO_DECLARADO = "supuesto declarado"


@dataclass(frozen=True, slots=True)
class Constante:
    """Una constante de cálculo con su fuente. Nunca un número suelto en el código."""

    id: str
    nombre: str
    valor: Decimal | str
    fuente: str

    def __post_init__(self) -> None:
        if not self.fuente.strip():
            raise ValueError(f"la constante {self.id} exige fuente o «{SUPUESTO_DECLARADO}»")

    @property
    def supuesto_declarado(self) -> bool:
        return self.fuente == SUPUESTO_DECLARADO


#: Fracción pintada de una línea discontinua: 3 m de línea por cada 8 m (3 pintados y 5 sin
#: pintar). No se cotejó con un manual de señalización venezolano.
FRACCION_PINTADA_DISCONTINUA = Constante(
    "V-1",
    "Fracción pintada de la línea discontinua (3 m de línea por cada 8 m)",
    Decimal("0.375"),
    SUPUESTO_DECLARADO,
)

#: Los códigos tienen la forma de la norma de carreteras (letra «C» y nueve dígitos), pero sus
#: números son provisionales y correlativos: no se tomaron del texto de la norma (fuentes del plan
#: vial, §3). No es la COVENIN 2000-92, que es la de edificaciones.
FUENTE_CODIGOS_VIALES = Constante(
    "V-2",
    "Forma de los códigos de partida viales",
    "C-xxx.xxx.xxx",
    "COVENIN 2000-1:1987, Parte I Carreteras: código a cotejar con el texto de la norma",
)

#: clave -> (código, descripción, unidad). La unidad es la de la cantidad que deriva el tramo.
PARTIDAS_VIALES: dict[str, tuple[str, str, str]] = {
    "fresado": ("C-000.000.001", "Fresado de pavimento asfáltico", "m3"),
    "base_granular": ("C-000.000.002", "Base granular compactada", "m3"),
    "subbase_granular": ("C-000.000.003", "Sub-base granular compactada", "m3"),
    "imprimacion": ("C-000.000.004", "Riego de imprimación", "m2"),
    "imprimacion_ligante": ("C-000.000.005", "Ligante del riego de imprimación", "l"),
    "riego_adherencia": ("C-000.000.006", "Riego de adherencia", "m2"),
    "riego_adherencia_ligante": ("C-000.000.007", "Ligante del riego de adherencia", "l"),
    "carpeta": ("C-000.000.008", "Carpeta de concreto asfáltico", "m2"),
    "carpeta_mezcla": ("C-000.000.009", "Mezcla asfáltica de la carpeta", "t"),
    "bacheo": ("C-000.000.010", "Bacheo con mezcla asfáltica", "m3"),
    "bacheo_mezcla": ("C-000.000.011", "Mezcla asfáltica del bacheo", "t"),
    "demarcacion_continua": ("C-000.000.012", "Demarcación con línea continua", "m"),
    "demarcacion_discontinua": ("C-000.000.013", "Demarcación con línea discontinua", "m"),
    "transporte_mezcla": (
        "C-000.000.014",
        "Transporte de mezcla asfáltica desde la planta",
        "t·km",
    ),
    # Tarea 16b (filas 34, 51 y 63): la pintura de cada línea de demarcación, para que VR5 se
    # dispare desde la interfaz. Código provisional y correlativo, como los demás.
    "pintura_demarcacion": ("C-000.000.015", "Pintura de demarcación", "l"),
    # F5 vial, tarea 1 (diseño 2026-11-03 §6): las seis partidas que traía el presupuesto vial
    # revisado en local. Códigos provisionales y correlativos (V-2). Movilización y señalización
    # no salen de la geometría (van a mano); las otras cuatro las deriva el tramo si da su dato.
    "movilizacion_equipos": ("C-000.000.016", "Movilización y desmovilización de equipos", "viaje"),
    "limpieza_superficie": ("C-000.000.017", "Limpieza de la superficie antes del riego", "m2"),
    "transporte_fresado": ("C-000.000.018", "Transporte del material fresado, medido suelto", "m3"),
    "senalizacion_transito": ("C-000.000.019", "Señalización y control de tránsito", "dia"),
    "captafaros": ("C-000.000.020", "Captafaros (ojos de gato)", "unidad"),
    "demarcacion_superficie": (
        "C-000.000.021",
        "Demarcación de superficies (pasos peatonales y líneas de pare)",
        "m2",
    ),
    # Variantes de medición (decisión provisional 4 del 2026-11-06): el fresado medido en área y
    # la colocación de la carpeta medida en masa. Código propio: CV2 suma por código sin convertir
    # unidades, así que la misma clave en dos unidades mezclaría m² con m³.
    "fresado_area": ("C-000.000.022", "Fresado de pavimento asfáltico, medido en área", "m2"),
    "carpeta_colocacion_masa": (
        "C-000.000.023",
        "Colocación de carpeta de concreto asfáltico, medida en masa",
        "t",
    ),
}


# --- Rangos de las reglas viales VR1 a VR7 (plan vial, Tarea 9; fuentes del plan, §4) -------------

_A_COTEJAR = "a cotejar con la especificación del proyecto"

#: VR1: diferencia relativa admitida entre las toneladas de carpeta del presupuesto y las derivadas.
TOLERANCIA_CARPETA = Constante(
    "V-3",
    "Tolerancia relativa de las toneladas de carpeta (VR1)",
    Decimal("0.005"),
    SUPUESTO_DECLARADO,
)

#: VR2: puntos de porcentaje admitidos sobre la fórmula de trabajo de la receta.
TOLERANCIA_ASFALTO_PUNTOS = Constante(
    "V-4",
    "Tolerancia del porcentaje de asfalto sobre la fórmula de trabajo, en puntos (VR2)",
    Decimal("0.5"),
    f"tolerancia contractual de LanammeUCR (Costa Rica), ±0,5 %; {_A_COTEJAR}",
)

#: VR3: ligante residual mínimo y máximo, en g/m².
IMPRIMACION_RESIDUAL_MIN_G_M2 = Constante(
    "V-5",
    "Ligante residual mínimo de la imprimación, g/m² (VR3)",
    Decimal("500"),
    f"IDU Bogotá 500-05 / pliego de Madrid; {_A_COTEJAR}",
)
IMPRIMACION_RESIDUAL_MAX_G_M2 = Constante(
    "V-6",
    "Ligante residual máximo de la imprimación con emulsión, g/m² (VR3)",
    Decimal("2000"),
    f"IDU Bogotá 610-18 / pliego de Madrid (1.000 a 2.000 g/m² según el suelo); {_A_COTEJAR}",
)
ADHERENCIA_RESIDUAL_MIN_G_M2 = Constante(
    "V-7",
    "Ligante residual mínimo del riego de adherencia, g/m² (VR3)",
    Decimal("200"),
    f"pliego de Madrid; {_A_COTEJAR}",
)
DENSIDAD_LIGANTE_KG_L = Constante(
    "V-8",
    "Densidad del producto ligante, kg/l (VR3)",
    Decimal("1.0"),
    f"{SUPUESTO_DECLARADO}; a cotejar con la ficha del producto",
)
FRACCION_RESIDUAL_EMULSION = Constante(
    "V-9",
    "Fracción residual de la emulsión asfáltica (VR3)",
    Decimal("0.60"),
    f"{SUPUESTO_DECLARADO}; a cotejar con la ficha del producto",
)

#: VR4: diferencia relativa admitida entre los t·km del presupuesto y toneladas × distancia.
TOLERANCIA_TRANSPORTE = Constante(
    "V-10",
    "Tolerancia relativa de los t·km de transporte (VR4)",
    Decimal("0.005"),
    SUPUESTO_DECLARADO,
)

#: VR5: litros de pintura por km de línea de 10 cm (rendimiento teórico, sin pérdidas).
PINTURA_MIN_L_KM = Constante(
    "V-11",
    "Pintura mínima, l por km de línea de 10 cm (VR5)",
    Decimal("29"),
    f"fichas técnicas de Comex, Hempel, Gruposur y Sherwin-Williams; {_A_COTEJAR}",
)
PINTURA_MAX_L_KM = Constante(
    "V-12",
    "Pintura máxima, l por km de línea de 10 cm (VR5)",
    Decimal("44"),
    f"fichas técnicas de Comex, Hempel, Gruposur y Sherwin-Williams; {_A_COTEJAR}",
)
ANCHO_LINEA_REFERENCIA_CM = Constante(
    "V-13",
    "Ancho de línea al que se refiere el rango de pintura, cm (VR5)",
    Decimal("10"),
    "las mismas fichas técnicas de V-11 y V-12, a cotejar con la ficha del producto",
)
ANCHO_LINEA_SUPUESTO_CM = Constante(
    "V-14",
    "Ancho de línea cuando la partida de pintura no lo declara, cm (VR5)",
    Decimal("10"),
    SUPUESTO_DECLARADO,
)

#: Litros de pintura que la derivación pone a cada línea de demarcación (Tarea 16b, filas 51 y 63):
#: el punto medio del rango de VR5 (V-11 y V-12), por km de línea de 10 cm.
PINTURA_POR_DEFECTO_L_KM = Constante(
    "V-17",
    "Pintura que se deriva por defecto, l por km de línea de 10 cm",
    Decimal("36.5"),
    f"{SUPUESTO_DECLARADO}: punto medio de V-11 y V-12; a cotejar con la ficha del producto",
)

# --- Tolerancias de la conciliación (plan vial, Tarea 10) -------------------------------------

#: CV1 y CV3: diferencia admitida, en la moneda del presupuesto, entre dos precios.
TOLERANCIA_PRECIO = Constante(
    "V-15",
    "Tolerancia de un precio, en la moneda del presupuesto (CV1 y CV3)",
    Decimal("0.01"),
    "plan vial, Tarea 10: un centavo",
)

#: CV2: diferencia relativa admitida entre la cantidad del presupuesto y la de los tramos.
TOLERANCIA_CANTIDAD_CONCILIADA = Constante(
    "V-16",
    "Tolerancia relativa de la cantidad de una partida frente a la suma de sus tramos (CV2)",
    Decimal("0.001"),
    f"{SUPUESTO_DECLARADO}; la misma de R1 (`TrazabilidadGeometrica`)",
)
