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

TIPOS_DEMARCACION = ("continua", "discontinua")

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
    de trabajo de la planta (Tarea 16b, filas 58 y 63)."""

    tipo: str
    espesor_m: Decimal | None
    densidad_t_m3: Decimal | None
    dosis_l_m2: Decimal | None
    asfalto_pct: Decimal | None = None

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
        for (nombre, valor), uso in zip(datos, _DATOS_POR_TIPO[self.tipo], strict=True):
            if valor is None:
                if uso == _OBLIGATORIO:
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


@dataclass(frozen=True, slots=True)
class Demarcacion:
    """Líneas de demarcación a lo largo de todo el tramo."""

    tipo: str
    lineas: int

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_DEMARCACION:
            raise ValueError(
                f"demarcación desconocida: {self.tipo!r} "
                f"(se esperaba {' o '.join(TIPOS_DEMARCACION)})"
            )
        if isinstance(self.lineas, bool) or not isinstance(self.lineas, int) or self.lineas < 1:
            raise ValueError(f"las lineas de demarcación deben ser un entero ≥ 1: {self.lineas!r}")


@dataclass(frozen=True, slots=True)
class Tramo:
    """Un tramo entre dos progresivas (en km), de ancho constante, con sus capas y su demarcación.

    `distancia_planta_km` es la distancia de transporte de la mezcla desde la planta; sin ella no
    se deriva el transporte.
    """

    id: str
    progresiva_ini_km: Decimal
    progresiva_fin_km: Decimal
    ancho_m: Decimal
    capas: tuple[Capa, ...]
    demarcacion: tuple[Demarcacion, ...] = ()
    distancia_planta_km: Decimal | None = None

    def __post_init__(self) -> None:
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
