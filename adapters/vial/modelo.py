"""Modelo de un tramo vial: progresivas, ancho, capas y demarcación (plan vial, Tarea 7).

Todo en `Decimal`. Cada objeto se valida al construirse y el error nombra el dato que falta o
sobra: lo que no sigue la convención se rechaza, no se adivina.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

TIPOS_CAPA = (
    "fresado",
    "base_granular",
    "subbase_granular",
    "imprimacion",
    "riego_adherencia",
    "carpeta",
    "bacheo",
)

#: «captafaros» (prueba de punta a punta del 2026-11-13): ojos de gato solos, sin línea ni pintura.
TIPOS_DEMARCACION = ("continua", "discontinua", "superficie", "captafaros")

#: Variantes de medición de una capa (F5 vial, decisión provisional 4 del 2026-11-06): por tipo, la
#: unidad de siempre y la otra que se admite. La de siempre se guarda como `None`.
MEDICIONES: dict[str, tuple[str, str]] = {"fresado": ("m3", "m2"), "carpeta": ("m2", "t")}
#: Convenciones del transporte de la mezcla (F5 vial, tarea 2): la de siempre, t·km (se guarda
#: `None`), o «banda»: la partida en t con la distancia como banda en su descripción.
TRANSPORTE_T_KM = "t·km"
TRANSPORTE_BANDA = "banda"

#: Capas que se riegan: solo ellas admiten la limpieza de la superficie (F5 vial, tarea 1).
CAPAS_DE_RIEGO = ("imprimacion", "riego_adherencia")

_OBLIGATORIO = "obligatorio"
_OPCIONAL = "opcional"
_NO_USA = "no usa"

#: Qué datos usa cada tipo de capa: (espesor, densidad, dosis, asfalto). El porcentaje de asfalto
#: del proyecto (Tarea 16b) es opcional y solo de las capas de mezcla asfáltica.
_DATOS_POR_TIPO: dict[str, tuple[str, str, str, str]] = {
    "fresado": (_OBLIGATORIO, _NO_USA, _NO_USA, _NO_USA),
    "base_granular": (_OBLIGATORIO, _NO_USA, _NO_USA, _NO_USA),
    "subbase_granular": (_OBLIGATORIO, _NO_USA, _NO_USA, _NO_USA),
    "imprimacion": (_NO_USA, _NO_USA, _OBLIGATORIO, _NO_USA),
    "riego_adherencia": (_NO_USA, _NO_USA, _OBLIGATORIO, _NO_USA),
    "carpeta": (_OBLIGATORIO, _OBLIGATORIO, _NO_USA, _OPCIONAL),
    "bacheo": (_OBLIGATORIO, _OPCIONAL, _NO_USA, _OPCIONAL),
}

#: `origen_id` es `String(120)` en la base; "tramo:<id>:demarcacion:<n>" debe caber.
LARGO_MAXIMO_ID = 80


def _positivo(nombre: str, valor: Decimal) -> None:
    if not isinstance(valor, Decimal):
        raise TypeError(f"{nombre} debe ser Decimal, no {type(valor).__name__}")
    if not valor.is_finite() or valor <= 0:
        raise ValueError(f"{nombre} debe ser un número mayor que cero: {valor}")


@dataclass(frozen=True, slots=True)
class Capa:
    """Una capa del paquete estructural o un riego, con los datos que su tipo usa.

    `asfalto_pct` es el porcentaje de asfalto que el proyecto pide a la mezcla de la carpeta o del
    bacheo, en puntos (5,5 es 5,5 %), mayor que 0 y menor que 100. VR2 lo compara con la fórmula
    de trabajo de la planta (Tarea 16b, filas 58 y 63).

    F5 vial, tarea 1 (diseño 2026-11-03 §6.3), todos opcionales:

    - `esponjamiento`: solo del fresado; el factor volumen suelto ÷ volumen en sitio (1,25), mayor
      o igual a 1. Sin valor por defecto (decisión provisional 3): sin él no se deriva el
      transporte del fresado.
    - `limpieza`: solo de la imprimación y del riego de adherencia; con ella se deriva la limpieza
      de la superficie (el área regada). Sin ella, el tramo deriva lo mismo que antes.
    - `medicion`: la unidad de la partida principal cuando no es la de siempre (`MEDICIONES`):
      «m2» para el fresado, «t» para la colocación de la carpeta. La de siempre se guarda `None`.

    Prueba de punta a punta del 2026-11-13 (D2), opcional:

    - `suministro`: solo de la imprimación y del riego de adherencia; el APU del riego ya trae el
      ligante («riego con suministro»), así que no se deriva la partida del ligante y la dosis
      deja de ser obligatoria (si está, VR3 la sigue midiendo). Sin él, la capa es la de siempre.
    """

    tipo: str
    espesor_m: Decimal | None
    densidad_t_m3: Decimal | None
    dosis_l_m2: Decimal | None
    asfalto_pct: Decimal | None = None
    esponjamiento: Decimal | None = None
    limpieza: bool = False
    medicion: str | None = None
    suministro: bool = False

    def __post_init__(self) -> None:
        if self.tipo not in _DATOS_POR_TIPO:
            raise ValueError(
                f"capa desconocida: {self.tipo!r} (se esperaba una de {', '.join(TIPOS_CAPA)})"
            )
        datos = (
            ("espesor", self.espesor_m),
            ("densidad", self.densidad_t_m3),
            ("dosis", self.dosis_l_m2),
            ("asfalto", self.asfalto_pct),
        )
        if not isinstance(self.suministro, bool):
            raise TypeError(
                f"el suministro de la capa {self.tipo} es sí o no, no {self.suministro!r}"
            )
        if self.suministro and self.tipo not in CAPAS_DE_RIEGO:
            raise ValueError(
                f"la capa {self.tipo} no usa suministro: solo la imprimación y el riego de "
                "adherencia"
            )
        for (nombre, valor), uso in zip(datos, _DATOS_POR_TIPO[self.tipo], strict=True):
            if valor is None:
                # con suministro, el ligante va dentro del APU del riego: la dosis es opcional
                if uso == _OBLIGATORIO and not (self.suministro and nombre == "dosis"):
                    raise ValueError(f"la capa {self.tipo} exige {nombre}")
                continue
            if uso == _NO_USA:
                raise ValueError(f"la capa {self.tipo} no usa {nombre}: déjelo vacío")
            _positivo(f"{nombre} de la capa {self.tipo}", valor)
        if self.asfalto_pct is not None and self.asfalto_pct >= 100:
            raise ValueError(
                f"asfalto de la capa {self.tipo} debe ser un porcentaje menor que 100: "
                f"{self.asfalto_pct}"
            )
        self._validar_f5()

    def _validar_f5(self) -> None:
        if self.esponjamiento is not None:
            if self.tipo != "fresado":
                raise ValueError(f"la capa {self.tipo} no usa esponjamiento: déjelo vacío")
            _positivo("esponjamiento del fresado", self.esponjamiento)
            if self.esponjamiento < 1:
                raise ValueError(
                    "el esponjamiento del fresado es el volumen suelto ÷ el volumen en sitio "
                    f"(por ejemplo 1,25) y debe ser mayor o igual a 1: {self.esponjamiento}"
                )
        if not isinstance(self.limpieza, bool):
            raise TypeError(f"la limpieza de la capa {self.tipo} es sí o no, no {self.limpieza!r}")
        if self.limpieza and self.tipo not in CAPAS_DE_RIEGO:
            raise ValueError(
                f"la capa {self.tipo} no usa limpieza: solo la imprimación y el riego de adherencia"
            )
        if self.medicion is None:
            return
        usual, otra = MEDICIONES.get(self.tipo, (None, None))
        if usual is None:
            raise ValueError(f"la capa {self.tipo} no admite otra medición: déjela vacía")
        if self.medicion == usual:
            object.__setattr__(self, "medicion", None)
        elif self.medicion != otra:
            raise ValueError(
                f"medición de la capa {self.tipo}: vacía ({usual}) o {otra}, no {self.medicion!r}"
            )


@dataclass(frozen=True, slots=True)
class Demarcacion:
    """Líneas de demarcación a lo largo de todo el tramo, o elementos de superficie.

    F5 vial, tarea 1 (diseño 2026-11-03 §6.3):

    - `superficie` (pasos peatonales, líneas de pare): `lineas` es el número de elementos iguales
      y `area_m2`, obligatoria, el área de cada uno. La cantidad es área × número.
    - `captafaros`: en una línea continua o discontinua, el número de ojos de gato que declara
      (decisión provisional 3: basta el número declarado; derivarlo de la separación es otra
      extensión).

    Prueba de punta a punta del 2026-11-13 (D2): con tipo `captafaros`, ojos de gato solos sobre
    una línea que no se pinta en esta obra: `captafaros` es el número (obligatorio) y `lineas` es
    1; no se deriva la línea ni su pintura.
    """

    tipo: str
    lineas: int
    area_m2: Decimal | None = None
    captafaros: int | None = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_DEMARCACION:
            raise ValueError(
                f"demarcación desconocida: {self.tipo!r} "
                f"(se esperaba {', '.join(TIPOS_DEMARCACION)})"
            )
        if isinstance(self.lineas, bool) or not isinstance(self.lineas, int) or self.lineas < 1:
            raise ValueError(f"las lineas de demarcación deben ser un entero ≥ 1: {self.lineas!r}")
        if self.tipo == "superficie":
            if self.area_m2 is None:
                raise ValueError("la demarcación de superficie exige el área de cada elemento")
            _positivo("el área de cada elemento de la demarcación", self.area_m2)
            if self.captafaros is not None:
                raise ValueError("la demarcación de superficie no usa captafaros: déjelos vacíos")
            return
        if self.tipo == "captafaros":
            if self.captafaros is None:
                raise ValueError("la demarcación de captafaros exige el número de captafaros")
            if self.lineas != 1:
                raise ValueError(
                    "la demarcación de captafaros no usa lineas: el número va en captafaros"
                )
        if self.area_m2 is not None:
            raise ValueError(f"la demarcación {self.tipo} no usa área: déjela vacía")
        if self.captafaros is not None and (
            isinstance(self.captafaros, bool)
            or not isinstance(self.captafaros, int)
            or self.captafaros < 1
        ):
            raise ValueError(f"los captafaros deben ser un entero ≥ 1: {self.captafaros!r}")


@dataclass(frozen=True, slots=True)
class Tramo:
    """Un tramo entre dos progresivas (en km), de ancho constante, con sus capas y su demarcación.

    `distancia_planta_km` es la distancia de transporte de la mezcla desde la planta; sin ella no
    se deriva el transporte en t·km.

    `transporte` es la convención con que la obra mide el transporte de la mezcla (F5 vial, tarea
    2): `None` es t·km, la de siempre; «banda» es en toneladas, con la distancia como banda en la
    descripción de la partida («más de 8 km y hasta 10 km»). Con banda, el tramo deriva la partida
    en t aunque no declare la distancia; VR4 usa la distancia para ver si cae en la banda.
    """

    id: str
    progresiva_ini_km: Decimal
    progresiva_fin_km: Decimal
    ancho_m: Decimal
    capas: tuple[Capa, ...]
    demarcacion: tuple[Demarcacion, ...] = ()
    distancia_planta_km: Decimal | None = None
    transporte: str | None = None

    def __post_init__(self) -> None:
        if self.transporte == TRANSPORTE_T_KM:
            object.__setattr__(self, "transporte", None)
        elif self.transporte not in (None, TRANSPORTE_BANDA):
            raise ValueError(
                f"tramo {self.id}: el transporte se mide en {TRANSPORTE_T_KM} (vacío) o por "
                f"{TRANSPORTE_BANDA}, no {self.transporte!r}"
            )
        if not self.id.strip():
            raise ValueError("el tramo necesita un id")
        if len(self.id) > LARGO_MAXIMO_ID:
            raise ValueError(f"el id del tramo pasa de {LARGO_MAXIMO_ID} caracteres: {self.id!r}")
        if ":" in self.id:
            # «:» separa las partes de `origen_id` («tramo:<id>:capa:<n>»): lo haría ambiguo.
            raise ValueError(f"el id del tramo no puede llevar «:»: {self.id!r}")
        for nombre in ("progresiva_ini_km", "progresiva_fin_km"):
            valor = getattr(self, nombre)
            if not isinstance(valor, Decimal) or not valor.is_finite():
                raise ValueError(f"tramo {self.id}: {nombre} debe ser un Decimal finito")
            if valor < 0:
                raise ValueError(f"tramo {self.id}: la {nombre} no puede ser negativa: {valor}")
        if self.progresiva_fin_km <= self.progresiva_ini_km:
            raise ValueError(
                f"tramo {self.id}: la progresiva final ({self.progresiva_fin_km}) debe ser mayor "
                f"que la inicial ({self.progresiva_ini_km})"
            )
        _positivo(f"tramo {self.id}: el ancho", self.ancho_m)
        if self.distancia_planta_km is not None:
            _positivo(f"tramo {self.id}: la distancia a la planta", self.distancia_planta_km)
        object.__setattr__(self, "capas", tuple(self.capas))
        object.__setattr__(self, "demarcacion", tuple(self.demarcacion))

    @property
    def longitud_m(self) -> Decimal:
        return (self.progresiva_fin_km - self.progresiva_ini_km) * 1000
