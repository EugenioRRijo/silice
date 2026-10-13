"""Contrato interno del adaptador `hoja_empresa` (spec 1.5 §5): lo que entrega el lector y lo que
recibe el escritor.

El lector convierte el libro de Excel de la empresa en un `LibroLeido`: todo dato lleva la celda de
la que salió
(`Celda`), para que cada hallazgo y cada fila de TRAZABILIDAD apunten a `HOJA!CELDA` (NORMAS §2,
principio 6). Los
números son `Decimal` (NORMAS §2.3): el lector convierte con `Decimal(str(valor))`, nunca desde un
`float` crudo.

El escritor recibe un `DatosDevolucion`: el libro leído más lo que calculó Silice (`fusion/`) con el
motor del
núcleo. Este módulo no importa nada fuera de la biblioteca estándar.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

__all__ = [
    "ApuCalculado",
    "ApuLeido",
    "Celda",
    "DatosDevolucion",
    "FilaAlerta",
    "FilaEspecial",
    "FilaHallazgo",
    "FilaTraza",
    "InsumoLeido",
    "LibroLeido",
    "LibroNoInterpretable",
    "LineaApu",
    "ParametrosLibro",
    "PartidaLeida",
    "Portada",
    "Rotulo",
    "TipoFilaEspecial",
    "TipoInsumo",
    "clave",
]


class LibroNoInterpretable(ValueError):  # noqa: N818 (nombre fijado por el contrato 1.5)
    """El libro pasó la guardia y se leyó, pero sus datos no permiten recalcularlo (por ejemplo, un
    FCAS menor que 1 o un APU que el motor no acepta). El mensaje está escrito para mostrarlo al
    usuario tal cual; la causa técnica va encadenada (`__cause__`)."""


def clave(hoja: str, ref: str) -> str:
    """Clave única de una celda en los mapas `formulas` y `valores`: `HOJA!REF`, sin `$`."""
    return f"{hoja}!{ref.replace('$', '')}"


@dataclass(frozen=True, slots=True)
class Celda:
    """Una celda del libro. `ref` va sin `$` (`G48`)."""

    hoja: str
    ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", self.ref.replace("$", ""))

    def __str__(self) -> str:
        return clave(self.hoja, self.ref)

    @property
    def origen_id(self) -> str:
        """El `origen_id` de un hallazgo o de un `ItemComputo` que sale de esta celda."""
        return str(self)


class TipoInsumo(StrEnum):
    """Prefijo de código de la hoja INSUMOS: MT-xx, MO-xx, EQ-xx."""

    MATERIAL = "MT"
    MANO_OBRA = "MO"
    EQUIPO = "EQ"


class Rotulo(StrEnum):
    """Los rótulos de un APU de la plantilla. El valor de cada uno vive en la columna G (F para
    REND)."""

    MAT = "MAT"  # Materiales (USD/u): subtotal de materiales, sin transporte
    MO = "MO"  # Mano de obra (USD/u) = base/día × FCAS ÷ rendimiento
    EQ = "EQ"  # Equipos y herramientas (USD/u) = equipos/día ÷ rendimiento + herramientas menores
    TR = "TR"  # Transporte y disposición (USD/u)
    CD = "CD"  # Costo directo total (USD/u)
    ADM = "ADM"  # Administración (USD/u)
    SUB = "SUB"  # Sub-total CD + administración (USD/u)
    UTI = "UTI"  # Utilidad e imprevistos (USD/u)
    PU = "PU"  # Precio unitario total (USD/u)
    REND = "REND"  # Rendimiento (u/día)
    ESC = "ESC"  # Escombro a botar, esponjado (m³/u)
    BASE_MO = "BASE_MO"  # Subtotal salarios base ($/día)
    EQ_DIA = "EQ_DIA"  # Subtotal equipos ($/día)
    HERR = "HERR"  # Herramientas menores ($/u)


@dataclass(frozen=True, slots=True)
class Portada:
    """Datos de la PORTADA (valores guardados, tal como los escribió la empresa)."""

    cliente: str = ""
    obra: str = ""
    contratista: str = ""
    ubicacion: str = ""
    norma: str = ""
    moneda: str = ""
    fecha_texto: str = ""


@dataclass(frozen=True, slots=True)
class ParametrosLibro:
    """Parámetros globales de INSUMOS (sección 4). `celdas` va por nombre definido: 'FCAS', 'HERR',
    'ADMON'…

    `fcas` es el FACTOR de la empresa (1,9 = la base se multiplica por 1,9); el núcleo recibe `fcas
    - 1`
    (spec 1.5, F-D1). Un parámetro que el libro no tiene vale 0 y no aparece en `celdas`.
    """

    fcas: Decimal
    herramientas: Decimal
    administracion: Decimal
    utilidad: Decimal
    iva: Decimal
    capacidad_camion: Decimal
    flete: Decimal
    tarifa_vertedero: Decimal
    celdas: Mapping[str, Celda] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InsumoLeido:
    """Una fila de INSUMOS. `celda` es la del precio; `fuente` es la columna FUENTE /
    OBSERVACIÓN."""

    codigo: str
    tipo: TipoInsumo
    descripcion: str
    unidad: str
    precio: Decimal
    fuente: str
    celda: Celda


@dataclass(frozen=True, slots=True)
class LineaApu:
    """Una línea de insumo dentro de un APU.

    `cantidad` es el consumo por unidad de partida (materiales) o la cuadrilla / cantidad por día
    (mano de obra y
    equipos). `precio` es el valor guardado que el APU muestra (P.U., jornal/día o costo/día): puede
    diferir de
    INSUMOS si el libro no estaba recalculado (L3).
    """

    tipo: TipoInsumo
    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio: Decimal
    celda_codigo: Celda
    celda_cantidad: Celda


@dataclass(frozen=True, slots=True)
class ApuLeido:
    """Una hoja APU tal como está en el libro, con la celda de cada rótulo.

    `fila_presupuesto` es la fila de PRESUPUESTO que nombra la fórmula de su título (`A2 =
    +PRESUPUESTO!Dnn`), o
    `None` si el título es texto (spec 1.5, F-D6). `administracion` y `utilidad` son las que usa
    ESTE APU (pueden
    ser un literal distinto del parámetro global: L6). `herramientas` es el % de herramientas
    menores (0 si el APU
    no tiene esa fila). `escombro` vale 0 si el APU no tiene bloque de transporte.
    """

    hoja: str
    titulo: str
    fila_presupuesto: int | None
    codigo_partida: str
    unidad: str
    rendimiento: Decimal
    lineas: tuple[LineaApu, ...]
    escombro: Decimal
    administracion: Decimal
    utilidad: Decimal
    herramientas: Decimal
    rotulos: Mapping[Rotulo, Celda] = field(default_factory=dict)
    guardados: Mapping[Rotulo, Decimal] = field(default_factory=dict)

    @property
    def ident(self) -> str:
        """Identificador para nombres definidos: 'APU-01' -> 'APU_01', 'APU-x' -> 'APU_X' (spec
        F-D5)."""
        return "APU_" + self.hoja.split("-", 1)[-1].upper().replace(" ", "_").replace("-", "_")


@dataclass(frozen=True, slots=True)
class PartidaLeida:
    """Un renglón de PRESUPUESTO. `guardados` va por letra de columna ('F', 'G', 'H'… 'Q', 'S')."""

    fila: int
    numero: int
    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    capitulo: str | None
    hoja_apu: str | None
    guardados: Mapping[str, Decimal] = field(default_factory=dict)


class TipoFilaEspecial(StrEnum):
    CAPITULO = "capitulo"
    SUBTOTAL = "subtotal"
    SUMA = "suma"  # fila de suma de partidas sin rótulo de capítulo (Q = SUM(...))
    TOTAL_SIN_IVA = "total_sin_iva"
    IVA = "iva"
    TOTAL = "total"


@dataclass(frozen=True, slots=True)
class FilaEspecial:
    """Una fila de PRESUPUESTO que no es partida: encabezado o subtotal de capítulo, totales."""

    fila: int
    texto: str
    tipo: TipoFilaEspecial
    valor: Decimal | None


@dataclass(frozen=True, slots=True)
class LibroLeido:
    """El libro completo. `formulas` y `valores` cubren TODAS las celdas no vacías, con clave
    `HOJA!REF`.

    `valores` guarda el valor guardado (Decimal para números, str para texto, None vacío).
    `programacion` guarda
    las entradas de CRONOGRAMA, CONTROL DE OBRA y PLAN DE PAGOS por nombre: 'DSEM', 'FRENTES',
    'SEMANA_CORTE',
    'TIEMPO_CONTRATADO', 'ANTICIPO', 'N_VALUACIONES', 'RETENCION' (solo las que el libro tiene).
    `ejecutado`,
    `final_previsto` y `gastado` van por número de partida (CONTROL DE OBRA secciones A y C, y
    GASTOS). `perfil` es el nombre del perfil de plantilla con que se leyó el libro
    (`adapters.hoja_empresa.perfil.cargar_perfil(libro.perfil)` lo recupera): todo consumidor lo
    toma de aquí y no supone otro.

    `apu(hoja)` e `insumo(codigo)` consultan índices armados una vez al crear el libro (si un nombre
    se repite, gana el primero, como en el recorrido lineal).
    """

    nombre: str
    sha256: str
    hojas: tuple[str, ...]
    portada: Portada
    parametros: ParametrosLibro
    insumos: tuple[InsumoLeido, ...]
    apus: tuple[ApuLeido, ...]
    partidas: tuple[PartidaLeida, ...]
    filas_especiales: tuple[FilaEspecial, ...]
    totales: Mapping[str, Decimal]
    nombres: Mapping[str, str]
    vinculos_externos: tuple[str, ...]
    formulas: Mapping[str, str]
    valores: Mapping[str, object]
    programacion: Mapping[str, Decimal] = field(default_factory=dict)
    ejecutado: Mapping[int, Decimal] = field(default_factory=dict)
    final_previsto: Mapping[int, Decimal] = field(default_factory=dict)
    gastado: Mapping[int, Decimal] = field(default_factory=dict)
    perfil: str = "arenaza"
    _por_hoja: Mapping[str, ApuLeido] = field(init=False, repr=False, compare=False)
    _por_codigo: Mapping[str, InsumoLeido] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        por_hoja: dict[str, ApuLeido] = {}
        for a in self.apus:
            por_hoja.setdefault(a.hoja, a)
        por_codigo: dict[str, InsumoLeido] = {}
        for i in self.insumos:
            por_codigo.setdefault(i.codigo, i)
        object.__setattr__(self, "_por_hoja", por_hoja)
        object.__setattr__(self, "_por_codigo", por_codigo)

    def apu(self, hoja: str) -> ApuLeido | None:
        return self._por_hoja.get(hoja)

    def insumo(self, codigo: str) -> InsumoLeido | None:
        return self._por_codigo.get(codigo)


# --- Lo que el escritor recibe --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApuCalculado:
    """Los componentes de un APU según Silice (motor del núcleo, spec F-D1), en USD/u salvo los
    `_dia`."""

    hoja: str
    materiales: Decimal  # sin transporte
    mano_obra: Decimal
    equipos: Decimal  # con herramientas menores
    transporte: Decimal
    costo_directo: Decimal
    administracion: Decimal
    subtotal: Decimal
    utilidad: Decimal
    precio_unitario: Decimal
    base_mo_dia: Decimal
    equipos_dia: Decimal
    herramientas: Decimal


@dataclass(frozen=True, slots=True)
class FilaHallazgo:
    """Una fila de la hoja AUDITORÍA. `accion`: 'corregido', 'a confirmar' o 'informado' (spec
    F-D7)."""

    codigo: str
    severidad: str
    descripcion: str
    celda: str
    impacto: Decimal | None
    accion: str


@dataclass(frozen=True, slots=True)
class FilaAlerta:
    """Una fila de la hoja ALERTAS USD-Bs (spec 1.5 §4). `tasa`/`precio_bs` son None si no hay
    tasa."""

    codigo: str
    descripcion: str
    tipo: str
    moneda: str
    precio: Decimal
    fecha: str
    fuente: str
    tasa: Decimal | None
    precio_bs: Decimal | None
    variacion: Decimal | None
    mensaje: str


@dataclass(frozen=True, slots=True)
class FilaTraza:
    """Una fila de la hoja TRAZABILIDAD: un dato, su valor y de dónde salió."""

    dato: str
    valor: str
    origen: str
    nota: str = ""


@dataclass(frozen=True, slots=True)
class DatosDevolucion:
    """Todo lo que el escritor necesita para el calcado.

    `apus` va por nombre de hoja; `precios_unitarios` por fila de PRESUPUESTO (el P.U. de Silice de
    cada
    partida); `totales` con las claves 'SUBSINIVA', 'IVATOT' y 'TOTALGEN' según Silice. `metadatos`
    lleva al menos
    'sha256_origen', 'version', 'fecha' y 'producido_por'.

    `reglas_evaluadas` son `(código, nombre)` de las reglas que corrieron; `reglas_no_evaluadas`,
    `(código, nombre, motivo)` de las que no (R11, R12, L10 u L11 según el caso): AUDITORÍA lista
    ambas. `moneda` es la del libro ('USD' o 'Bs'), la de los impactos de AUDITORÍA.
    """

    libro: LibroLeido
    apus: Mapping[str, ApuCalculado]
    precios_unitarios: Mapping[int, Decimal]
    totales: Mapping[str, Decimal]
    hallazgos: tuple[FilaHallazgo, ...] = ()
    alertas: tuple[FilaAlerta, ...] = ()
    trazabilidad: tuple[FilaTraza, ...] = ()
    metadatos: Mapping[str, str] = field(default_factory=dict)
    reglas_evaluadas: tuple[tuple[str, str], ...] = ()
    reglas_no_evaluadas: tuple[tuple[str, str, str], ...] = ()
    moneda: str = "USD"
