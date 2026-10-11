"""Modelo espacial de la hoja de metrajes (spec §6.1 y §6.2).

Metros, eje z hacia arriba desde el piso terminado. Toda dimensión es `Decimal` (NORMAS.md §2.3):
un valor que no lo sea se rechaza al construir, nunca se convierte. Todo es inmutable; las
colecciones son tuplas ordenadas por id para que dos espacios iguales en contenido sean iguales.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from adapters.espacio.origen import OrigenMedida, clave_esp, pares


class Especialidad(StrEnum):
    AGUA = "agua"
    DATOS = "datos"
    ELECTRICIDAD = "electricidad"


class TipoFuente(StrEnum):
    ACOMETIDA_AGUA = "acometida_agua"
    MONTANTE_AGUA = "montante_agua"
    COLECTOR_DRENAJE = "colector_drenaje"
    RACK = "rack"
    TABLERO = "tablero"


class TipoPunto(StrEnum):
    AGUA_FRIA = "agua_fria"
    DRENAJE = "drenaje"
    DATOS = "datos"
    TOMACORRIENTE = "tomacorriente"
    ILUMINACION = "iluminacion"


class SuperficiePunto(StrEnum):
    PARED = "pared"
    TECHO = "techo"
    PISO = "piso"


class SuperficieTramo(StrEnum):
    PARED = "pared"
    TECHO = "techo"
    PLAFON = "plafon"
    PISO = "piso"
    BANDEJA = "bandeja"


class ModoRecorrido(StrEnum):
    PROPUESTO = "propuesto"
    DECLARADO = "declarado"


#: Tolerancia geométrica de la hoja, en metros (spec §6.1).
TOLERANCIA = Decimal("0.001")

#: Único valor admitido de la especificación «llave_de_paso» de un punto de agua fría.
LLAVE_DE_PASO = "si"


def _decimal(valor: object, nombre: str) -> Decimal:
    """Exige un `Decimal` finito. Ni `float`, ni `int`, ni `str`, ni `bool`: nunca se convierten."""
    if not isinstance(valor, Decimal):
        raise TypeError(f"{nombre} debe ser Decimal, no {type(valor).__name__}")
    if not valor.is_finite():
        raise ValueError(f"{nombre} debe ser finito: {valor}")
    return valor


def _positivo(valor: object, nombre: str) -> Decimal:
    numero = _decimal(valor, nombre)
    if numero <= 0:
        raise ValueError(f"{nombre} debe ser positivo: {numero}")
    return numero


def _no_vacio(valor: str, nombre: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nombre} no puede estar vacío")


@dataclass(frozen=True, slots=True)
class Coord:
    x: Decimal
    y: Decimal
    z: Decimal

    def __post_init__(self) -> None:
        _decimal(self.x, "x")
        _decimal(self.y, "y")
        _decimal(self.z, "z")

    def distancia(self, otra: Coord) -> Decimal:
        dx, dy, dz = otra.x - self.x, otra.y - self.y, otra.z - self.z
        return (dx * dx + dy * dy + dz * dz).sqrt()


@dataclass(frozen=True, slots=True)
class Ambiente:
    """Rectángulo en planta con su altura (§6.1). Los no rectangulares se descomponen."""

    id: str
    nombre: str
    x0: Decimal
    y0: Decimal
    largo: Decimal
    ancho: Decimal
    alto: Decimal
    origen_id: str

    def __post_init__(self) -> None:
        _no_vacio(self.id, "el id del ambiente")
        _decimal(self.x0, "x0")
        _decimal(self.y0, "y0")
        _positivo(self.largo, "largo")
        _positivo(self.ancho, "ancho")
        _positivo(self.alto, "alto")

    def contiene(self, p: Coord, tolerancia: Decimal = TOLERANCIA) -> bool:
        """True si `p` está dentro del ambiente, con la tolerancia de §6.1 (borde incluido)."""
        t = tolerancia
        return (
            self.x0 - t <= p.x <= self.x0 + self.largo + t
            and self.y0 - t <= p.y <= self.y0 + self.ancho + t
            and -t <= p.z <= self.alto + t
        )


@dataclass(frozen=True, slots=True)
class Fuente:
    id: str
    especialidad: Especialidad
    tipo: TipoFuente
    ambiente_id: str
    posicion: Coord
    origen_id: str

    def __post_init__(self) -> None:
        _no_vacio(self.id, "el id de la fuente")
        object.__setattr__(self, "especialidad", Especialidad(self.especialidad))
        object.__setattr__(self, "tipo", TipoFuente(self.tipo))
        if not isinstance(self.posicion, Coord):
            raise TypeError("la posición de la fuente debe ser una Coord con Decimal")


@dataclass(frozen=True, slots=True)
class Circuito:
    id: str
    tablero: str
    numero: int
    conductores: tuple[int, int, int]  # fase, neutro, tierra
    calibre: str
    puntos_maximos: int
    orden: tuple[str, ...] = ()  # ids de punto en el orden de la cadena

    def __post_init__(self) -> None:
        _no_vacio(self.id, "el id del circuito")
        if len(self.conductores) != 3 or any(c < 0 for c in self.conductores):
            raise ValueError("conductores es (fase, neutro, tierra), cada uno >= 0")
        if self.puntos_maximos < 1:
            raise ValueError("puntos_maximos debe ser >= 1")
        object.__setattr__(self, "conductores", tuple(self.conductores))
        object.__setattr__(self, "orden", tuple(self.orden))


@dataclass(frozen=True, slots=True)
class Punto:
    """Una salida de la especialidad (§6.2). `especificaciones`: diámetro, calibre, categoría…"""

    id: str
    nombre: str
    especialidad: Especialidad
    tipo: TipoPunto
    ambiente_id: str
    superficie: SuperficiePunto
    posicion: Coord
    origen_id: str
    fuente_id: str | None = None
    circuito_id: str | None = None
    especificaciones: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _no_vacio(self.id, "el id del punto")
        object.__setattr__(self, "especialidad", Especialidad(self.especialidad))
        object.__setattr__(self, "tipo", TipoPunto(self.tipo))
        object.__setattr__(self, "superficie", SuperficiePunto(self.superficie))
        object.__setattr__(self, "especificaciones", pares(self.especificaciones))
        llave = dict(self.especificaciones).get("llave_de_paso")
        if llave is not None and llave != LLAVE_DE_PASO:
            raise ValueError(f"llave_de_paso solo admite {LLAVE_DE_PASO!r}, no {llave!r}")
        if not isinstance(self.posicion, Coord):
            raise TypeError("la posición del punto debe ser una Coord con Decimal")

    @property
    def espec(self) -> Mapping[str, str]:
        return dict(self.especificaciones)


@dataclass(frozen=True, slots=True)
class Tramo:
    """Tramo de un recorrido. La longitud se calcula de los vértices; no se escribe a mano."""

    orden: int
    superficie: SuperficieTramo
    vertices: tuple[Coord, ...]
    empotrado: bool | None = None
    pendiente: Decimal | None = None  # drenaje

    def __post_init__(self) -> None:
        object.__setattr__(self, "superficie", SuperficieTramo(self.superficie))
        object.__setattr__(self, "vertices", tuple(self.vertices))
        if len(self.vertices) < 2 or not all(isinstance(v, Coord) for v in self.vertices):
            raise ValueError("un tramo necesita al menos dos vértices (Coord)")
        if self.pendiente is not None:
            _decimal(self.pendiente, "pendiente")

    @property
    def longitud(self) -> Decimal:
        return sum(
            (a.distancia(b) for a, b in zip(self.vertices, self.vertices[1:], strict=False)),
            Decimal(0),
        )


@dataclass(frozen=True, slots=True)
class Recorrido:
    """Camino de un punto o de un circuito. Propuesto: la geometría (1.4) lo calcula; declarado:
    los tramos los escribió el usuario."""

    id: str
    modo: ModoRecorrido
    punto_id: str | None = None
    circuito_id: str | None = None
    tramos: tuple[Tramo, ...] = ()

    def __post_init__(self) -> None:
        _no_vacio(self.id, "el id del recorrido")
        if (self.punto_id is None) == (self.circuito_id is None):
            raise ValueError("un recorrido pertenece a un punto o a un circuito, no a ambos")
        object.__setattr__(self, "modo", ModoRecorrido(self.modo))
        ordenes = [t.orden for t in self.tramos]
        if len(ordenes) != len(set(ordenes)):
            raise ValueError(f"el recorrido {self.id!r} repite el orden de un tramo: {ordenes}")
        object.__setattr__(self, "tramos", tuple(sorted(self.tramos, key=lambda t: t.orden)))


@dataclass(frozen=True, slots=True)
class SobrescrituraSegmento:
    """Diámetro o empotrado fijado a mano para un segmento, por su clave (§6.5)."""

    clave: str
    diametro: str | None = None
    empotrado: bool | None = None

    def __post_init__(self) -> None:
        _no_vacio(self.clave, "la clave del segmento")


def _ordenado(filas: Iterable, clave: str = "id") -> tuple:
    return tuple(sorted(filas, key=lambda f: getattr(f, clave)))


@dataclass(frozen=True, slots=True)
class Espacio:
    """El modelo espacial de una versión de presupuesto. Vacío por defecto (FR-1)."""

    origenes: tuple[OrigenMedida, ...] = field(default=())
    ambientes: tuple[Ambiente, ...] = field(default=())
    fuentes: tuple[Fuente, ...] = field(default=())
    circuitos: tuple[Circuito, ...] = field(default=())
    puntos: tuple[Punto, ...] = field(default=())
    recorridos: tuple[Recorrido, ...] = field(default=())
    sobrescrituras: tuple[SobrescrituraSegmento, ...] = field(default=())

    def __post_init__(self) -> None:
        for nombre in ("origenes", "ambientes", "fuentes", "circuitos", "puntos", "recorridos"):
            object.__setattr__(self, nombre, _ordenado(getattr(self, nombre)))
        object.__setattr__(self, "sobrescrituras", _ordenado(self.sobrescrituras, "clave"))
        self._exigir_ids_unicos()
        self._exigir_referencias()

    @property
    def vacio(self) -> bool:
        return not any(
            (
                self.origenes,
                self.ambientes,
                self.fuentes,
                self.circuitos,
                self.puntos,
                self.recorridos,
                self.sobrescrituras,
            )
        )

    def _exigir_ids_unicos(self) -> None:
        for nombre in ("origenes", "ambientes", "fuentes", "circuitos", "puntos", "recorridos"):
            repetidos = [
                i for i, n in Counter(f.id for f in getattr(self, nombre)).items() if n > 1
            ]
            if repetidos:
                raise ValueError(f"ids repetidos en {nombre}: {sorted(repetidos)}")
        claves = [s.clave for s in self.sobrescrituras]
        if len(claves) != len(set(claves)):
            raise ValueError("claves repetidas en sobrescrituras")

    def _exigir_referencias(self) -> None:
        # el origen de medida es el unico enlace que no se exige aqui: la fila sin origen o con un
        # origen que no esta registrado se acepta en la version y R8 la marca ERROR (RF-44, UC-13a)
        ambientes = {a.id for a in self.ambientes}
        fuentes = {f.id for f in self.fuentes}
        puntos = {p.id for p in self.puntos}
        circuitos = {c.id for c in self.circuitos}

        def exigir(existe: bool, que: str, quien: str, ref: str) -> None:
            if not existe:
                raise ValueError(f"{quien} cita {que} inexistente: {ref!r}")

        for f in self.fuentes:
            exigir(f.ambiente_id in ambientes, "un ambiente", f"la fuente {f.id!r}", f.ambiente_id)
        for p in self.puntos:
            quien = f"el punto {p.id!r}"
            exigir(p.ambiente_id in ambientes, "un ambiente", quien, p.ambiente_id)
            if p.fuente_id is not None:
                exigir(p.fuente_id in fuentes, "una fuente", quien, p.fuente_id)
            if p.circuito_id is not None:
                exigir(p.circuito_id in circuitos, "un circuito", quien, p.circuito_id)
        for c in self.circuitos:
            for pid in c.orden:
                exigir(pid in puntos, "un punto", f"el circuito {c.id!r}", pid)
        for r in self.recorridos:
            quien = f"el recorrido {r.id!r}"
            if r.punto_id is not None:
                exigir(r.punto_id in puntos, "un punto", quien, r.punto_id)
            if r.circuito_id is not None:
                exigir(r.circuito_id in circuitos, "un circuito", quien, r.circuito_id)

    def validar(self) -> list[tuple[str, str]]:
        """Pares `(clave_esp, mensaje)` de las filas fuera de su ambiente (tolerancia de §6.1).

        Es informativo: no lanza ni impide guardar. Las reglas R8/R9 (tarea 1.6) lo usan o recorren
        el modelo con `Ambiente.contiene()`; la clave (`esp_puntos:P1`, formato de
        `origen.clave_esp`) es la que citan en `origen_ids` (spec §8.2). «Ambiente sin puntos» no
        se informa: un borrador empieza por el ambiente y ninguna regla lo pide.
        """
        ambientes = {a.id: a for a in self.ambientes}
        problemas: list[tuple[str, str]] = []
        for f in self.fuentes:
            if not ambientes[f.ambiente_id].contiene(f.posicion):
                problemas.append(
                    (
                        clave_esp("esp_fuentes", f.id),
                        f"fuente {f.id}: fuera del ambiente {f.ambiente_id}",
                    )
                )
        for p in self.puntos:
            if not ambientes[p.ambiente_id].contiene(p.posicion):
                problemas.append(
                    (
                        clave_esp("esp_puntos", p.id),
                        f"punto {p.id}: fuera del ambiente {p.ambiente_id}",
                    )
                )
        return problemas
