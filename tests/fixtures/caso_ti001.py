"""Caso TI-001: laptops HP, canalización EMT, cableado UTP Cat 6 y servidor en rack.

Caso construido para el proyecto (NORMAS.md §1): la oficina, la topología, los rendimientos y el
plan son supuestos declarados; no es una obra ejecutada. Los precios son las referencias publicadas
MaPreX de julio de 2026 (materiales y equipos al 09/07/2026, mano de obra al 01/07/2026), en Bs,
convertidas a USD con la tasa que declara el propio listado: 633,3644 Bs/USD al 01/07/2026. Cada
insumo cita su Ref de MaPreX entre corchetes para rastrearlo hasta el PDF.

Única copia de estos datos en el sistema (NORMAS.md §2, principio DRY): la importan
`scripts/analisis_ti001.py`, `scripts/informe_ti001.py` y `tests/unit/test_caso_ti001.py`.

Flujo: `data/samples/telecom/topologia_ti001.csv` --AdaptadorTelecom--> ItemComputo trazables;
`COMPOSICIONES` + `PARAMETROS` + `PLAN` --core.budget.elaborar--> presupuesto, curva e informe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from adapters.telecom import AdaptadorTelecom
from core.budget import ResultadoElaboracion, elaborar
from core.budget.curva import PeriodoPlan
from core.contracts import (
    ComposicionAPU,
    ItemComputo,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)

RAIZ = Path(__file__).resolve().parents[2]
RUTA_TOPOLOGIA = RAIZ / "data" / "samples" / "telecom" / "topologia_ti001.csv"

#: Bs/USD al 01/07/2026, declarada en el listado MaPreX de mano de obra.
TASA = Decimal("633.3644")
FECHA = date(2026, 9, 30)
CODIGO = "TI-001"
MONEDA = "USD"
CUATRO_DECIMALES = Decimal("0.0001")


def usd(bolivares: str) -> Decimal:
    """Bs de MaPreX -> USD con la tasa declarada, a cuatro decimales (como `referencia_*.csv`)."""
    return (Decimal(bolivares) / TASA).quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Insumo:
    """Un renglón de los listados MaPreX, con su precio en Bs tal como aparece en el PDF."""

    tipo: str  # material | equipo | mano_obra
    descripcion: str
    unidad: str
    precio_bs: str
    ref: str
    depreciacion: str = "1"  # solo equipos: columna Cop/Depr. de equipos.pdf
    bono_bs: str = "0"  # solo mano de obra: columna Bono de mano_de_obra.pdf

    @property
    def precio(self) -> Decimal:
        return usd(self.precio_bs)

    @property
    def bono(self) -> Decimal:
        return usd(self.bono_bs)

    @property
    def etiqueta(self) -> str:
        return f"{self.descripcion} [{self.ref}]"


def _mat(descripcion: str, unidad: str, precio_bs: str, ref: str) -> Insumo:
    return Insumo("material", descripcion, unidad, precio_bs, ref)


def _eq(descripcion: str, precio_bs: str, ref: str, depreciacion: str) -> Insumo:
    return Insumo("equipo", descripcion, "dia", precio_bs, ref, depreciacion)


def _mo(descripcion: str, jornal_bs: str, ref: str, bono_bs: str) -> Insumo:
    return Insumo("mano_obra", descripcion, "dia", jornal_bs, ref, bono_bs=bono_bs)


INSUMOS: dict[str, Insumo] = {
    # Canalización EMT
    "emt1": _mat("Tubo EMT 1 pulg acero liviano galvanizado", "m", "5508.54", "ELE307"),
    "anillo1": _mat("Anillo EMT 1 pulg", "pza", "2265.00", "ELE028"),
    "conector1": _mat("Conector EMT 1 pulg", "pza", "2416.00", "ELE184"),
    "curva1": _mat("Curva EMT 1 pulg", "pza", "5360.50", "ELE206"),
    "abraz1": _mat("Abrazadera sencilla conduit 1 pulg", "pza", "528.50", "TUB223"),
    "cajapaso": _mat("Caja de paso/derivacion 6x6x4 pulg", "pza", "11551.50", "ELE324"),
    "emt34": _mat("Tubo EMT 3/4 pulg acero liviano galvanizado", "m", "3020.00", "ELE311"),
    "anillo34": _mat("Anillo EMT 3/4 pulg", "pza", "943.75", "ELE034"),
    "conector34": _mat("Conector EMT 3/4 pulg", "pza", "1132.50", "MT251"),
    "curva34": _mat("Curva EMT 3/4 pulg", "pza", "3148.35", "ELE211"),
    "abraz34": _mat("Abrazadera sencilla conduit 3/4 pulg", "pza", "528.50", "TUB222"),
    # Salida de datos y cableado
    "cajetin": _mat(
        "Cajetin cuadrado metalico 4x4 pulg salida 3/4 pulg", "pza", "1947.90", "ELF066"
    ),
    "faceplate": _mat("Face plate para 1 toma de red", "und", "1510.00", "ELA640"),
    "jack": _mat("Jack coupler hembra RJ45 cat 6", "und", "1510.00", "ELC065"),
    "utp": _mat("Cable UTP voz/dato 4 pares cat 6", "m", "1510.00", "ELA006"),
    "tirrap": _mat("Tirrap amarre plastico 3,5 x 200 mm", "pza", "60.40", "QUI059"),
    "etiqueta": _mat("Etiqueta de identificacion 5x2 cm", "pza", "302.00", "ELE142"),
    "pc05": _mat("Patch cord cat 6 de 0,5 m", "und", "1434.50", "ELA629"),
    "pc2": _mat("Patch cord cat 6 de 2 m", "und", "3020.00", "ELA628"),
    # Rack y equipos activos
    "rack": _mat(
        "Rack de piso 19 pulg cerrado 42 posiciones para servidor", "und", "607020.00", "ELC050"
    ),
    "patchpanel": _mat("Patch panel 24 puertos cat 6", "und", "33220.00", "ELC057"),
    "organizador": _mat("Organizador horizontal de cables para rack", "und", "164590.00", "ELC046"),
    "regleta": _mat("Regleta multitoma para rack 8 tomas", "pza", "33975.00", "ELA296"),
    "bandeja": _mat("Bandeja ventilada para rack 19x19", "und", "21140.00", "ELC047"),
    "switch": _mat(
        "Switch 48 puertos 10/100 con 2 puertos gigabit administrable",
        "und",
        "846355.00",
        "ELC059",
    ),
    "ups": _mat("UPS 3000 VA 45 minutos para rack", "und", "998110.00", "ELC012"),
    # Suministros tomados de equipos.pdf (precio de adquisición: entran como material)
    "servidor": _mat(
        "Servidor en rack HP ProLiant o similar (ref. MaPreX: computador servidor en rack i7)",
        "und",
        "2265000.00",
        "OFI131",
    ),
    "laptop": _mat(
        "Laptop HP i7 o similar (ref. MaPreX: computador tipo laptop i7)",
        "und",
        "1510000.00",
        "OFI058",
    ),
    # Equipos (precio x factor Cop/Depr. de equipos.pdf)
    "dobladora": _eq("Dobladora de tubo EMT 1/2 a 1 1/2 pulg", "3775.00", "ELE030", "1"),
    "taladro": _eq("Equipos: taladro, tester y medicion electrica", "302000.00", "ALB020", "0.01"),
    "escalera": _eq("Escalera de aluminio tipo tijera 7 tramos", "157040.00", "SUB071", "0.009"),
    "herramientas": _eq("Herramientas menores", "9060.00", "ALB213", "1"),
    "ponchadora": _eq(
        "Ponchadora de impacto para cable estructurado", "13937.30", "ELE047", "0.007"
    ),
    "certificador": _eq("Certificador de cable UTP 6/5e", "37750.00", "MED022", "0.005"),
    "pc_config": _eq(
        "Computador PC/laptop por dia (estacion de configuracion)", "5285.00", "EZ0507", "1"
    ),
    # Mano de obra (jornal y bono de mano_de_obra.pdf)
    "maestro": _mo("Maestro electricista N7", "1470.34", "24-216", "3597.51"),
    "electricista": _mo("Electricista de 1ra N5", "1385.63", "19-215", "3679.85"),
    "ayudante": _mo("Ayudante N2", "1128.42", "1-1.2", "3939.53"),
    "tecnico": _mo("Tecnico de redes", "6333.64", "ESP010", "1480.67"),
}

#: El contrato admite un solo bono por obrero; se adopta el del oficio predominante (electricista
#: de 1ra N5). El efecto de la simplificación lo cuantifica `scripts/analisis_ti001.py`.
BONO_ADOPTADO = INSUMOS["electricista"].bono

PARAMETROS = ParametrosCosto(
    fcas=Decimal("6.00"),  # 600 %: el de la línea base del sistema (decisión D4)
    bono_alimentacion=BONO_ADOPTADO,
    administracion=Decimal("0.15"),
    utilidad=Decimal("0.10"),
)


def _m(clave: str, cantidad: str) -> LineaMaterial:
    insumo = INSUMOS[clave]
    return LineaMaterial(insumo.etiqueta, insumo.unidad, Decimal(cantidad), insumo.precio)


def _e(clave: str, cantidad: str = "1") -> LineaEquipo:
    insumo = INSUMOS[clave]
    return LineaEquipo(
        insumo.etiqueta, Decimal(cantidad), insumo.precio, Decimal(insumo.depreciacion)
    )


def _o(clave: str, cantidad: str) -> LineaManoObra:
    insumo = INSUMOS[clave]
    return LineaManoObra(insumo.etiqueta, Decimal(cantidad), insumo.precio)


_CUADRILLA_ELECTRICA = (_o("maestro", "0.25"), _o("electricista", "1"), _o("ayudante", "1"))
_EQUIPOS_CANALIZACION = (_e("dobladora"), _e("taladro"), _e("escalera"), _e("herramientas"))

COMPOSICIONES: dict[str, ComposicionAPU] = {
    "TI-EMT1": ComposicionAPU(
        "TI-EMT1",
        "Suministro e instalacion de tuberia EMT 1 pulg a la vista con accesorios (troncales)",
        "m",
        Decimal("25"),
        materiales=(
            _m("emt1", "1"),
            _m("anillo1", "0.3333"),
            _m("conector1", "0.10"),
            _m("curva1", "0.08"),
            _m("abraz1", "0.50"),
            _m("cajapaso", "0.03"),
        ),
        equipos=_EQUIPOS_CANALIZACION,
        mano_obra=_CUADRILLA_ELECTRICA,
    ),
    "TI-EMT34": ComposicionAPU(
        "TI-EMT34",
        "Suministro e instalacion de tuberia EMT 3/4 pulg a la vista con accesorios (bajantes)",
        "m",
        Decimal("20"),
        materiales=(
            _m("emt34", "1"),
            _m("anillo34", "0.3333"),
            _m("conector34", "0.35"),
            _m("curva34", "0.35"),
            _m("abraz34", "0.50"),
        ),
        equipos=_EQUIPOS_CANALIZACION,
        mano_obra=_CUADRILLA_ELECTRICA,
    ),
    "TI-PTO": ComposicionAPU(
        "TI-PTO",
        "Salida de datos cat 6: cajetin 4x4 pulg, face plate y jack RJ45 cat 6",
        "punto",
        Decimal("8"),
        materiales=(_m("cajetin", "1"), _m("faceplate", "1"), _m("jack", "1")),
        equipos=(_e("ponchadora"), _e("taladro"), _e("herramientas")),
        mano_obra=(_o("electricista", "1"), _o("ayudante", "1")),
    ),
    "TI-UTP": ComposicionAPU(
        "TI-UTP",
        "Suministro y tendido de cable UTP cat 6 por tuberia",
        "m",
        Decimal("150"),
        materiales=(_m("utp", "1"), _m("tirrap", "0.5")),
        equipos=(_e("escalera"), _e("herramientas")),
        mano_obra=(_o("electricista", "1"), _o("ayudante", "1")),
    ),
    "TI-CERT": ComposicionAPU(
        "TI-CERT",
        "Terminacion en patch panel, etiquetado y certificacion de enlace permanente cat 6",
        "punto",
        Decimal("12"),
        materiales=(_m("pc05", "1"), _m("etiqueta", "2")),
        equipos=(_e("certificador"), _e("ponchadora"), _e("herramientas")),
        mano_obra=(_o("tecnico", "1"), _o("ayudante", "1")),
    ),
    "TI-RACK": ComposicionAPU(
        "TI-RACK",
        "Suministro y armado de rack de piso 19 pulg cerrado 42U con patch panel cat 6, "
        "organizador, regleta y bandeja",
        "pieza",
        Decimal("1"),
        materiales=(
            _m("rack", "1"),
            _m("patchpanel", "1"),
            _m("organizador", "1"),
            _m("regleta", "1"),
            _m("bandeja", "1"),
            _m("tirrap", "50"),
        ),
        equipos=(_e("taladro"), _e("herramientas")),
        mano_obra=(_o("electricista", "1"), _o("ayudante", "1"), _o("tecnico", "0.5")),
    ),
    "TI-UPS": ComposicionAPU(
        "TI-UPS",
        "Suministro, montaje en rack y prueba de UPS 3000 VA",
        "pieza",
        Decimal("2"),
        materiales=(_m("ups", "1"),),
        equipos=(_e("taladro"), _e("herramientas")),
        mano_obra=(_o("electricista", "1"), _o("ayudante", "1")),
    ),
    "TI-SW": ComposicionAPU(
        "TI-SW",
        "Suministro, montaje y configuracion de switch administrable 48 puertos",
        "pieza",
        Decimal("1"),
        materiales=(_m("switch", "1"), _m("pc05", "2")),
        equipos=(_e("pc_config"), _e("herramientas")),
        mano_obra=(_o("tecnico", "1"),),
    ),
    "TI-SRV": ComposicionAPU(
        "TI-SRV",
        "Suministro, montaje en rack, instalacion de sistema operativo y configuracion de "
        "servidor HP en rack",
        "pieza",
        Decimal("0.5"),
        materiales=(_m("servidor", "1"), _m("pc05", "2")),
        equipos=(_e("pc_config"), _e("herramientas")),
        mano_obra=(_o("tecnico", "1"), _o("ayudante", "0.5")),
    ),
    "TI-LAP": ComposicionAPU(
        "TI-LAP",
        "Suministro, configuracion (imagen, dominio, antivirus) y puesta en servicio de "
        "laptop HP i7",
        "pieza",
        Decimal("6"),
        materiales=(_m("laptop", "1"), _m("pc2", "1")),
        equipos=(_e("pc_config"),),
        mano_obra=(_o("tecnico", "1"),),
    ),
}

#: Orden de presentación de las partidas (y numeración 01-10 del informe).
ORDEN = (
    "TI-EMT1",
    "TI-EMT34",
    "TI-PTO",
    "TI-UTP",
    "TI-RACK",
    "TI-UPS",
    "TI-SW",
    "TI-SRV",
    "TI-LAP",
    "TI-CERT",
)

#: Frente que ejecuta cada partida: dos frentes trabajan en paralelo.
FRENTE = {
    **dict.fromkeys(("TI-EMT1", "TI-EMT34", "TI-PTO", "TI-UTP", "TI-UPS"), "Cuadrilla electrica"),
    **dict.fromkeys(("TI-RACK", "TI-SW", "TI-SRV", "TI-LAP", "TI-CERT"), "Tecnico de redes"),
}

D = Decimal
#: Plan de trabajo de 10 días hábiles: (período, [(partida, fracción ejecutada en el período)]).
PLAN: list[PeriodoPlan] = [
    ("Dia 1", [("TI-EMT1", D("0.45")), ("TI-RACK", D("1"))]),
    ("Dia 2", [("TI-EMT1", D("0.45")), ("TI-UPS", D("1")), ("TI-SW", D("0.5"))]),
    (
        "Dia 3",
        [
            ("TI-EMT1", D("0.10")),
            ("TI-EMT34", D("0.40")),
            ("TI-SW", D("0.5")),
            ("TI-SRV", D("0.25")),
        ],
    ),
    ("Dia 4", [("TI-EMT34", D("0.45")), ("TI-SRV", D("0.50"))]),
    (
        "Dia 5",
        [
            ("TI-EMT34", D("0.15")),
            ("TI-PTO", D("0.45")),
            ("TI-SRV", D("0.25")),
            ("TI-LAP", D("0.25")),
        ],
    ),
    ("Dia 6", [("TI-PTO", D("0.55")), ("TI-UTP", D("0.15")), ("TI-LAP", D("0.50"))]),
    ("Dia 7", [("TI-UTP", D("0.40")), ("TI-LAP", D("0.25"))]),
    ("Dia 8", [("TI-UTP", D("0.45"))]),
    ("Dia 9", [("TI-CERT", D("0.60"))]),
    ("Dia 10", [("TI-CERT", D("0.40"))]),
]


def items(ruta: Path = RUTA_TOPOLOGIA) -> list[ItemComputo]:
    """Las cantidades de la topología, extraídas por el adaptador telecom."""
    return AdaptadorTelecom().extraer(ruta)


def elaborar_caso(
    parametros: ParametrosCosto = PARAMETROS,
    composiciones: dict[str, ComposicionAPU] | None = None,
    computo: list[ItemComputo] | None = None,
) -> ResultadoElaboracion:
    """Presupuesto, curva e informe de auditoría del caso (el informe se genera siempre)."""
    return elaborar(
        computo if computo is not None else items(),
        composiciones if composiciones is not None else COMPOSICIONES,
        parametros,
        CODIGO,
        FECHA,
        MONEDA,
        plan=PLAN,
    )
