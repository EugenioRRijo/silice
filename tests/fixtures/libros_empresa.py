"""Libros de Excel sintéticos con la forma de la plantilla de la empresa (Silice 1.5).

Los libros reales de ARENAZA son confidenciales y NO están en el repositorio (spec 1.5 §6,
NORMAS §1): ninguna prueba los lee. Este módulo fabrica libros **ficticios** con la misma
estructura que describe el análisis de causas raíz
(`docs/auditoria/2026-10-13-causas-raiz-libros-arenaza.md`, "Cómo funcionan los libros"):
PORTADA, INSUMOS con los nombres definidos (`FCAS`, `HERR`, `ADMON`, `UTIL`, `IVA`, `CAMION`,
`FLETE`, `VERT`, `PRECIOS`), un `APU-nn` por partida con `VLOOKUP` a
`PRECIOS`, PRESUPUESTO con `INDIRECT("'APU-"&TEXT($B5,"00")&"'!G..")`, RESUMEN, MEDICIONES,
CRONOGRAMA, PROCURA, PLAN DE PAGOS y AUX. Todos los nombres, la obra, el cliente y la contratista
son inventados; no hay RIF.

Cada celda con fórmula lleva su **valor guardado** (XlsxWriter escribe la fórmula y el valor), igual
que un libro que Excel guardó recalculado. Los valores guardados los calcula este módulo con
`Decimal` (aritmética propia, independiente del adaptador y del motor del núcleo) y, para el libro
limpio, se contrastan al construirlo contra la memoria de cálculo escrita a mano de abajo
(`MEMORIA`): si la aritmética del generador se desviara de la memoria, el generador falla.

Los errores de los libros reales (H1-H18) se **siembran** uno a uno con `Siembra`, para que cada
regla L1-L9 tenga su error y su frontera.

Memoria de cálculo del libro limpio (parámetros: FCAS 1,9; HERR 0,05; ADMON 0,10; UTIL 0,10;
IVA 0,16; CAMION 6 m³; FLETE 60 USD; VERT 2 USD/m³)::

    APU-01  Friso liso (m2), rendimiento 10 u/día, cantidad 120
      MAT  = 0,2 × 10 + 0,05 × 25                       = 3,25
      MO   = (1 × 20 + 1 × 15) × 1,9 ÷ 10               = 6,65
      EQ   = 0,5 × 30 ÷ 10 + 0,05 × 6,65                = 1,5 + 0,3325 = 1,8325
      TR   = 0,02 × (60 ÷ 6) + 0,02 × 2                 = 0,2 + 0,04 = 0,24
      CD   = 3,25 + 6,65 + 1,8325 + 0,24                = 11,9725
      ADM  = 1,19725 ; SUB = 13,16975 ; UTI = 1,316975 ; PU = 14,486725
      monto = 120 × 14,486725                           = 1 738,407
    APU-02  Pared de bloque (m2), rendimiento 8, cantidad 80, sin bloque de transporte
      MAT  = 0,1 × 10 + 0,02 × 25 + 12,5 × 0,8          = 11,5
      MO   = (1 × 20 + 2 × 15) × 1,9 ÷ 8                = 11,875
      EQ   = 2 × 4 ÷ 8 + 0,05 × 11,875                  = 1 + 0,59375 = 1,59375
      CD   = 24,96875 ; ADM = 2,496875 ; SUB = 27,465625 ; UTI = 2,7465625
      PU   = 30,2121875 ; monto = 80 × 30,2121875       = 2 416,975
    APU-03  Demolición de friso (m2), rendimiento 20, cantidad 50, sin materiales ni equipos
      MO   = 2 × 15 × 1,9 ÷ 20                          = 2,85
      EQ   = 0,05 × 2,85                                = 0,1425
      TR   = 0,03 × 10 + 0,03 × 2                       = 0,36
      CD   = 3,3525 ; ADM = 0,33525 ; SUB = 3,68775 ; UTI = 0,368775 ; PU = 4,056525
      monto = 50 × 4,056525                             = 202,82625
    SUBSINIVA = 1 738,407 + 2 416,975 + 202,82625       = 4 358,20825
    IVATOT    = 0,16 × 4 358,20825                      = 697,31332
    TOTALGEN  = 4 358,20825 + 697,31332                 = 5 055,52157
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any

__all__ = [
    "APUS_LIMPIOS",
    "D",
    "FILA_PRIMERA_PARTIDA",
    "INSUMOS",
    "MEMORIA",
    "PALETA",
    "PARAMETROS",
    "ApuSint",
    "Construido",
    "Insumo",
    "PartidaSinApu",
    "Siembra",
    "construir_libro",
    "libro_limpio",
]


def D(x: str | int) -> Decimal:  # noqa: N802 - atajo de lectura en las pruebas
    return Decimal(str(x))


#: Paleta de la plantilla (perfil `arenaza`, estilo.paleta): la misma que debe calcar el escritor.
PALETA = {
    "titulo": "501C1C",
    "encabezado": "7F2D2D",
    "subtotal": "FBEFD6",
    "editable": "FFF6DD",
    "total": "E9C1C1",
    "texto": "1F2328",
    "blanco": "FFFFFF",
}


@dataclass(frozen=True)
class Insumo:
    codigo: str
    descripcion: str
    unidad: str
    precio: Decimal
    fuente: str


#: INSUMOS ficticios. MT-03 dice «REFERENCIAL — ajustar» y EQ-01 no tiene fuente (alertas §4.1).
INSUMOS: tuple[Insumo, ...] = (
    Insumo("MT-01", "Cemento gris tipo I (ficticio)", "saco", D("10"), "Cotización ficticia A"),
    Insumo("MT-02", "Arena lavada (ficticia)", "m3", D("25"), "Cotización ficticia A"),
    Insumo("MT-03", "Bloque de arcilla 15 cm (ficticio)", "und", D("0.8"), "REFERENCIAL — ajustar"),
    Insumo("MO-01", "Albañil de primera (ficticio)", "día", D("20"), "Tabulador ficticio"),
    Insumo("MO-02", "Ayudante (ficticio)", "día", D("15"), "Tabulador ficticio"),
    Insumo("MO-03", "Instalador a destajo (ficticio)", "m2", D("3"), "Tabulador ficticio"),
    Insumo("EQ-01", "Mezcladora de 1 saco (ficticia)", "día", D("30"), ""),
    Insumo("EQ-02", "Andamio tubular (ficticio)", "día", D("4"), "Alquiler ficticio"),
)

#: Parámetros globales de INSUMOS: nombre definido -> valor.
PARAMETROS: dict[str, Decimal] = {
    "FCAS": D("1.9"),
    "HERR": D("0.05"),
    "ADMON": D("0.10"),
    "UTIL": D("0.10"),
    "IVA": D("0.16"),
    "CAMION": D("6"),
    "FLETE": D("60"),
    "VERT": D("2"),
}


@dataclass(frozen=True)
class ApuSint:
    """Un APU del libro sintético y la fila de PRESUPUESTO que lo usa.

    `escombro=None` es un APU sin bloque de transporte (los APU reales tienen más de diez formas).
    `mano_obra_destajo` son líneas de mano de obra pagadas por m² fuera del subtotal de salarios
    base. `factores` multiplica el subtotal de una línea por un literal escrito en la fórmula
    (`"*1.1"`, `"/8"`), como en los libros reales (RL-8).
    """

    numero: int
    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    rendimiento: Decimal
    materiales: tuple[tuple[str, Decimal], ...] = ()
    mano_obra: tuple[tuple[str, Decimal], ...] = ()
    equipos: tuple[tuple[str, Decimal], ...] = ()
    escombro: Decimal | None = None
    hoja: str = ""
    mano_obra_destajo: tuple[tuple[str, Decimal], ...] = ()
    factores: Mapping[str, str] = field(default_factory=dict)
    # Siembras del APU
    utilidad_literal: Decimal | None = None  # H2/H18: utilidad escrita a mano (L6)
    divisor_equipos: Decimal | None = None  # H12: `=G27/12` en vez de ÷ rendimiento (L6)
    cd_sin_equipos: bool = False  # H1: el CD omite los equipos (L4, F1, L9)
    fila_titulo: int | None = None  # A2 = +PRESUPUESTO!D<otra fila> (L2)
    delta_cd_guardado: Decimal = Decimal(0)  # CD guardado = suma + delta (frontera de L4)
    en_presupuesto: bool = True  # False: hoja de plantilla sin partida (RL-4, L2 INFO)

    @property
    def nombre_hoja(self) -> str:
        return self.hoja or f"APU-{self.numero:02d}"


@dataclass(frozen=True)
class PartidaSinApu:
    """Una fila de PRESUPUESTO sin hoja APU (L2): P y monto escritos a mano."""

    numero: int
    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio: Decimal


APUS_LIMPIOS: tuple[ApuSint, ...] = (
    ApuSint(
        numero=1,
        codigo="E.311.000.001",
        descripcion="Friso liso en paredes (ficticio)",
        unidad="m2",
        cantidad=D("120"),
        rendimiento=D("10"),
        materiales=(("MT-01", D("0.2")), ("MT-02", D("0.05"))),
        mano_obra=(("MO-01", D("1")), ("MO-02", D("1"))),
        equipos=(("EQ-01", D("0.5")),),
        escombro=D("0.02"),
    ),
    ApuSint(
        numero=2,
        codigo="E.321.000.002",
        descripcion="Pared de bloque de arcilla (ficticia)",
        unidad="m2",
        cantidad=D("80"),
        rendimiento=D("8"),
        materiales=(("MT-01", D("0.1")), ("MT-02", D("0.02")), ("MT-03", D("12.5"))),
        mano_obra=(("MO-01", D("1")), ("MO-02", D("2"))),
        equipos=(("EQ-02", D("2")),),
        escombro=None,
    ),
    ApuSint(
        numero=3,
        codigo="E.041.000.003",
        descripcion="Demolición de friso (ficticia)",
        unidad="m2",
        cantidad=D("50"),
        rendimiento=D("20"),
        mano_obra=(("MO-02", D("2")),),
        escombro=D("0.03"),
    ),
)

#: Memoria de cálculo a mano del libro limpio (ver la cabecera). Oráculo de las pruebas.
MEMORIA: dict[str, Any] = {
    "componentes": {
        "APU-01": {
            "MAT": D("3.25"),
            "MO": D("6.65"),
            "EQ": D("1.8325"),
            "TR": D("0.24"),
            "CD": D("11.9725"),
            "ADM": D("1.19725"),
            "SUB": D("13.16975"),
            "UTI": D("1.316975"),
            "PU": D("14.486725"),
        },
        "APU-02": {
            "MAT": D("11.5"),
            "MO": D("11.875"),
            "EQ": D("1.59375"),
            "TR": D("0"),
            "CD": D("24.96875"),
            "ADM": D("2.496875"),
            "SUB": D("27.465625"),
            "UTI": D("2.7465625"),
            "PU": D("30.2121875"),
        },
        "APU-03": {
            "MAT": D("0"),
            "MO": D("2.85"),
            "EQ": D("0.1425"),
            "TR": D("0.36"),
            "CD": D("3.3525"),
            "ADM": D("0.33525"),
            "SUB": D("3.68775"),
            "UTI": D("0.368775"),
            "PU": D("4.056525"),
        },
    },
    "montos": {1: D("1738.407"), 2: D("2416.975"), 3: D("202.82625")},
    "SUBSINIVA": D("4358.20825"),
    "IVATOT": D("697.31332"),
    "TOTALGEN": D("5055.52157"),
}

#: Primera fila de partidas en PRESUPUESTO (la fila 4 es el capítulo).
FILA_PRIMERA_PARTIDA = 5


@dataclass(frozen=True)
class Siembra:
    """Errores sembrados a nivel de libro (los del APU van en `ApuSint`)."""

    # PRESUPUESTO
    p_guardado: Mapping[int, Decimal] = field(default_factory=dict)  # P guardado ≠ APU (L3/F1)
    rend_guardado: Mapping[int, Decimal] = field(default_factory=dict)  # F guardado viejo (L3)
    p_fila_fija: int | None = None  # todas las P leen G<fila> por INDIRECT (H6/H9, L1)
    rend_fila_fija: int | None = None  # todas las F (REND.) leen F<fila> (H9, L1)
    verificacion: Mapping[int, Decimal] = field(default_factory=dict)  # R ≠ 0 (L9)
    desglose_delta: Mapping[int, Decimal] = field(default_factory=dict)  # L guardado + delta (L9)
    partidas_sin_apu: tuple[PartidaSinApu, ...] = ()
    # Otras hojas
    cronograma_fila_rend: int | None = None  # CRONOGRAMA lee F<fila> fija (H6, L1)
    aux_escombro_celda: Mapping[int, str] = field(default_factory=dict)  # AUX lee otra celda (H8)
    resumen_ref_rota: bool = False  # RESUMEN con =PRESUPUESTO!#REF! (H10, L5)
    nombres_externos: tuple[str, ...] = ()  # MEDP1… -> [1]Hoja (H11, L5)
    nombres_rotos: tuple[str, ...] = ()  # nombre -> #REF! (L5)
    vinculo_externo: str | None = None  # pieza xl/externalLinks/_rels con este Target (L5)
    formula_externa: bool = False  # MEDICIONES lee [1]Hoja1!A1 (L5 ADVERTENCIA)
    mediciones_literales: tuple[str, ...] = ()  # fórmulas como "=9.73*2.75" (H12, L7)
    procura_dif: Decimal = Decimal(0)  # "Dif. vs presupuesto materiales" (H7, L9)
    procura_dif_solo_total: Decimal = Decimal(0)  # solo "Dif. vs Costo Directo" (L9)
    plan_dif: Decimal = Decimal(0)  # "Verificación" de PLAN DE PAGOS (L9)
    resumen_composicion_delta: Decimal = Decimal(0)  # composición ≠ subtotal (H3, L9)
    # PORTADA
    fecha_texto: str = "Julio 2026"
    moneda: str = "Dólares de los Estados Unidos de América (USD)"
    cliente: str = "Condominio Ejemplo (ficticio)"
    contratista: str = "Constructora Didáctica (ficticia)"
    ubicacion: str = "Calle Ficticia 123, Ciudad Ejemplo"
    obra: str = "Rehabilitación de fachada — obra ficticia"
    insumos: tuple[Insumo, ...] = INSUMOS
    parametros: Mapping[str, Decimal] = field(default_factory=lambda: dict(PARAMETROS))
    sin_parametros: tuple[str, ...] = ()  # nombres definidos que no se crean
    autor: str = "Autor Ficticio"
    cabecera_compacta: bool = False  # cabecera del APU en las filas 3-4 (no en 4-6)
    #: Celdas reescritas al final, `"HOJA!A1": (valor guardado, fórmula | None)`: siembra libre.
    parches: Mapping[str, tuple[Any, str | None]] = field(default_factory=dict)


# --- Modelo de celdas ---------------------------------------------------------------------------


def _col(letras: str) -> int:
    n = 0
    for ch in letras:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _letra(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


@dataclass
class _C:
    valor: Any  # Decimal, str o None
    formula: str | None = None
    formato: str = "texto"


class _Hoja:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.celdas: dict[tuple[int, str], _C] = {}
        self.anchos: dict[str, float] = {}

    def pon(
        self, fila: int, col: str, valor: Any, formula: str | None = None, fmt: str = ""
    ) -> Any:
        if not fmt:
            fmt = "numero" if isinstance(valor, Decimal) else "texto"
        self.celdas[(fila, col)] = _C(valor, formula, fmt)
        return valor

    def v(self, fila: int, col: str) -> Any:
        c = self.celdas.get((fila, col))
        return None if c is None else c.valor


def _q(nombre: str) -> str:
    return f"'{nombre}'"


# --- APU ------------------------------------------------------------------------------------------


@dataclass
class FilasApu:
    """Filas de los rótulos de un APU generado (para sembrar desalineaciones en las pruebas)."""

    lineas: dict[str, int] = field(default_factory=dict)
    sub_mat: int = 0
    base: int = 0
    rend: int = 0
    costo_mo: int = 0
    sub_mo: int = 0
    eq_dia: int = 0
    herr: int = 0
    sub_eq: int = 0
    esc: int | None = None
    flete: int | None = None
    disp: int | None = None
    sub_tr: int | None = None
    mat_r: int = 0
    mo_r: int = 0
    eq_r: int = 0
    tr_r: int = 0
    cd: int = 0
    adm: int = 0
    sub: int = 0
    uti: int = 0
    pu: int = 0


@dataclass
class ValoresApu:
    MAT: Decimal = Decimal(0)
    MO: Decimal = Decimal(0)
    EQ: Decimal = Decimal(0)
    TR: Decimal = Decimal(0)
    CD: Decimal = Decimal(0)
    ADM: Decimal = Decimal(0)
    SUB: Decimal = Decimal(0)
    UTI: Decimal = Decimal(0)
    PU: Decimal = Decimal(0)


def _insumo(s: Siembra, codigo: str) -> Insumo:
    return next(i for i in s.insumos if i.codigo == codigo)


def _factor(texto: str) -> Decimal:
    if texto.startswith("*"):
        return Decimal(texto[1:])
    if texto.startswith("/"):
        return 1 / Decimal(texto[1:])
    raise ValueError(texto)


def _apu(
    h: _Hoja, a: ApuSint, s: Siembra, fila_partida: int | None, desc_partida: str
) -> tuple[FilasApu, ValoresApu]:
    p = s.parametros
    filas = FilasApu()
    fv = ValoresApu()
    h.anchos = {"A": 6, "B": 12, "C": 42, "D": 9, "E": 11, "F": 13, "G": 15}
    h.pon(1, "A", "ANÁLISIS DE PRECIO UNITARIO (APU)", fmt="titulo")
    fila_t = a.fila_titulo or fila_partida
    if fila_t is None:
        h.pon(2, "A", "PARTIDA DE EJEMPLO (plantilla)", fmt="subtitulo")
    else:
        h.pon(2, "A", desc_partida, formula=f"=+PRESUPUESTO!D{fila_t}", fmt="subtitulo")
    if s.cabecera_compacta:
        # Variante: la cabecera ocupa las filas 3 y 4 (sin Moneda/Norma/Cliente/Fecha).
        h.pon(3, "A", "Código de partida:")
        h.pon(3, "B", a.codigo)
        h.pon(4, "A", "Unidad:")
        h.pon(4, "B", a.unidad)
        r = 5
    else:
        # La cabecera de la plantilla: filas 4 a 6, con un segundo bloque de rótulos en E.
        h.pon(4, "A", "Código de partida:")
        h.pon(4, "B", a.codigo)
        h.pon(4, "E", "Norma de referencia:")
        h.pon(4, "F", "COVENIN 2000 (referencial)")
        h.pon(5, "A", "Unidad:")
        h.pon(5, "B", a.unidad)
        h.pon(5, "E", "Cliente:")
        h.pon(5, "F", s.cliente)
        h.pon(6, "A", "Moneda:")
        h.pon(6, "B", "USD ($)")
        h.pon(6, "E", "Fecha:")
        h.pon(6, "F", s.fecha_texto)
        r = 8

    def encabezado(fila: int, textos: tuple[str, ...]) -> None:
        for k, t in enumerate(textos):
            h.pon(fila, _letra(k), t, fmt="encabezado")

    def linea(fila: int, item: int, codigo: str, cant: Decimal) -> Decimal:
        ins = _insumo(s, codigo)
        h.pon(fila, "A", Decimal(item), fmt="entero")
        h.pon(fila, "B", codigo)
        h.pon(fila, "C", ins.descripcion, formula=f"=VLOOKUP(B{fila},PRECIOS,2,0)")
        h.pon(fila, "D", ins.unidad, formula=f"=VLOOKUP(B{fila},PRECIOS,3,0)")
        h.pon(fila, "E", cant, fmt="editable")
        h.pon(fila, "F", ins.precio, formula=f"=VLOOKUP(B{fila},PRECIOS,4,0)")
        sufijo = a.factores.get(codigo, "")
        sub = cant * ins.precio * (_factor(sufijo) if sufijo else 1)
        h.pon(fila, "G", sub, formula=f"=E{fila}*F{fila}{sufijo}")
        filas.lineas[codigo] = fila
        return sub

    # 1. Materiales
    h.pon(r, "A", "1.  MATERIALES", fmt="seccion")
    r += 1
    encabezado(r, ("Ítem", "Código", "Descripción", "Unidad", "Cantidad", "P.U. (USD)", "Subtotal"))
    r += 1
    ini = r
    mat = Decimal(0)
    for k, (cod, cant) in enumerate(a.materiales, start=1):
        mat += linea(r, k, cod, cant)
        r += 1
    filas.sub_mat = r
    rango = f"=SUM(G{ini}:G{r - 1})" if a.materiales else "=0"
    h.pon(r, "A", "SUBTOTAL MATERIALES (USD/u)", fmt="subtotal")
    h.pon(r, "G", mat, formula=rango, fmt="subtotal_num")
    r += 2

    # 2. Mano de obra
    h.pon(r, "A", "2.  MANO DE OBRA  (cuadrilla por día)", fmt="seccion")
    r += 1
    encabezado(
        r, ("Ítem", "Código", "Descripción", "Unidad", "Cuadrilla", "Jornal/día", "Total/día")
    )
    r += 1
    ini = r
    base = Decimal(0)
    for k, (cod, cant) in enumerate(a.mano_obra, start=1):
        base += linea(r, k, cod, cant)
        r += 1
    fin_base = r - 1
    destajo = Decimal(0)
    filas_destajo: list[int] = []
    for k, (cod, cant) in enumerate(a.mano_obra_destajo, start=len(a.mano_obra) + 1):
        destajo += linea(r, k, cod, cant)
        filas_destajo.append(r)
        r += 1
    filas.base = r
    h.pon(r, "A", "Subtotal salarios base ($/día)")
    h.pon(r, "G", base, formula=f"=SUM(G{ini}:G{fin_base})" if a.mano_obra else "=0")
    r += 1
    filas.rend = r
    h.pon(r, "A", "FCAS × Rendimiento (u/día)")
    h.pon(r, "E", p["FCAS"], formula="=FCAS")
    h.pon(r, "F", a.rendimiento, fmt="editable")
    r += 1
    filas.costo_mo = r
    mo = base * p["FCAS"] / a.rendimiento + destajo
    extra = "".join(f"+G{f}" for f in filas_destajo)
    h.pon(r, "A", "Costo mano de obra ($/u) = Base × FCAS ÷ Rendimiento")
    h.pon(r, "G", mo, formula=f"=G{filas.base}*E{filas.rend}/F{filas.rend}{extra}")
    r += 1
    filas.sub_mo = r
    h.pon(r, "A", "SUBTOTAL MANO DE OBRA (USD/u)", fmt="subtotal")
    h.pon(r, "G", mo, formula=f"=G{filas.costo_mo}", fmt="subtotal_num")
    r += 2

    # 3. Equipos
    h.pon(r, "A", "3.  EQUIPOS Y HERRAMIENTAS  (costo por día)", fmt="seccion")
    r += 1
    encabezado(r, ("Ítem", "Código", "Descripción", "Unidad", "Cantidad", "Costo/día", "Total/día"))
    r += 1
    ini = r
    eq_dia = Decimal(0)
    for k, (cod, cant) in enumerate(a.equipos, start=1):
        eq_dia += linea(r, k, cod, cant)
        r += 1
    filas.eq_dia = r
    h.pon(r, "A", "Subtotal equipos ($/día)")
    h.pon(r, "G", eq_dia, formula=f"=SUM(G{ini}:G{r - 1})" if a.equipos else "=0")
    r += 1
    filas.herr = r
    herr = p["HERR"] * mo
    h.pon(r, "A", "Herramientas menores (% de la mano de obra) ($/u)")
    h.pon(r, "F", p["HERR"], formula="=HERR", fmt="porcentaje")
    h.pon(r, "G", herr, formula=f"=F{r}*G{filas.sub_mo}")
    r += 1
    filas.sub_eq = r
    divisor = a.divisor_equipos if a.divisor_equipos is not None else None
    if divisor is not None:
        eq = eq_dia / divisor + herr
        f_eq = f"=G{filas.eq_dia}/{divisor}+G{filas.herr}"
    else:
        eq = eq_dia / a.rendimiento + herr
        f_eq = f"=G{filas.eq_dia}/F{filas.rend}+G{filas.herr}"
    h.pon(r, "A", "SUBTOTAL EQUIPOS Y HERRAMIENTAS (USD/u)", fmt="subtotal")
    h.pon(r, "G", eq, formula=f_eq, fmt="subtotal_num")
    r += 2

    # 4. Transporte
    tr = Decimal(0)
    if a.escombro is not None:
        h.pon(r, "A", "4.  TRANSPORTE Y DISPOSICIÓN DE ESCOMBROS", fmt="seccion")
        r += 1
        filas.esc = r
        h.pon(r, "A", "Escombro a botar, esponjado (m³/u)")
        h.pon(r, "G", a.escombro, fmt="editable")
        r += 1
        filas.flete = r
        flete = p["FLETE"] * a.escombro / p["CAMION"]
        h.pon(r, "A", "Flete a vertedero ($/u) = FLETE × Escombro ÷ CAMION")
        h.pon(r, "G", flete, formula=f"=FLETE*G{filas.esc}/CAMION")
        r += 1
        filas.disp = r
        disp = a.escombro * p["VERT"]
        h.pon(r, "A", "Derecho de disposición ($/u) = Escombro × VERT")
        h.pon(r, "G", disp, formula=f"=G{filas.esc}*VERT")
        r += 1
        filas.sub_tr = r
        tr = flete + disp
        h.pon(r, "A", "SUBTOTAL TRANSPORTE Y DISPOSICIÓN (USD/u)", fmt="subtotal")
        h.pon(r, "G", tr, formula=f"=G{filas.flete}+G{filas.disp}", fmt="subtotal_num")
        r += 2

    # Resumen
    h.pon(r, "A", "RESUMEN DE COSTOS", fmt="seccion")
    r += 1
    filas.mat_r = r
    h.pon(r, "A", "Materiales (USD/u)")
    h.pon(r, "G", mat, formula=f"=G{filas.sub_mat}")
    r += 1
    filas.mo_r = r
    h.pon(r, "A", "Mano de obra (USD/u)")
    h.pon(r, "G", mo, formula=f"=G{filas.sub_mo}")
    r += 1
    filas.eq_r = r
    h.pon(r, "A", "Equipos y herramientas (USD/u)")
    h.pon(r, "G", eq, formula=f"=G{filas.sub_eq}")
    r += 1
    filas.tr_r = r
    h.pon(r, "A", "Transporte y disposición (USD/u)")
    if filas.sub_tr is not None:
        h.pon(r, "G", tr, formula=f"=G{filas.sub_tr}")
    else:
        h.pon(r, "G", Decimal(0))
    r += 1
    filas.cd = r
    if a.cd_sin_equipos:
        cd = mat + mo + tr
        f_cd = f"=G{filas.mat_r}+G{filas.mo_r}+G{filas.tr_r}"
    else:
        cd = mat + mo + eq + tr
        f_cd = f"=SUM(G{filas.mat_r}:G{filas.tr_r})"
    cd += a.delta_cd_guardado
    h.pon(r, "A", "COSTO DIRECTO TOTAL (USD/u)", fmt="subtotal")
    h.pon(r, "G", cd, formula=f_cd, fmt="subtotal_num")
    r += 1
    filas.adm = r
    adm = cd * p["ADMON"]
    h.pon(r, "A", "Administración y gastos generales")
    h.pon(r, "F", p["ADMON"], formula="=ADMON", fmt="porcentaje")
    h.pon(r, "G", adm, formula=f"=G{filas.cd}*F{r}")
    r += 1
    filas.sub = r
    sub = cd + adm
    h.pon(r, "A", "SUB-TOTAL (Costo Directo + Administración) (USD/u)")
    h.pon(r, "G", sub, formula=f"=G{filas.cd}+G{filas.adm}")
    r += 1
    filas.uti = r
    if a.utilidad_literal is not None:
        u = a.utilidad_literal
        h.pon(r, "F", u, fmt="porcentaje")
    else:
        u = p["UTIL"]
        h.pon(r, "F", u, formula="=UTIL", fmt="porcentaje")
    uti = sub * u
    h.pon(r, "A", "Utilidad e imprevistos (sobre sub-total)")
    h.pon(r, "G", uti, formula=f"=G{filas.sub}*F{r}")
    r += 1
    filas.pu = r
    pu = sub + uti
    h.pon(r, "A", "PRECIO UNITARIO TOTAL (USD/u)", fmt="total")
    h.pon(r, "G", pu, formula=f"=G{filas.sub}+G{filas.uti}", fmt="total_num")
    r += 2
    h.pon(r, "A", "Nota: libro sintético de prueba; datos ficticios.", fmt="nota")
    fv.MAT, fv.MO, fv.EQ, fv.TR, fv.CD = mat, mo, eq, tr, cd
    fv.ADM, fv.SUB, fv.UTI, fv.PU = adm, sub, uti, pu
    return filas, fv


# --- Libro ----------------------------------------------------------------------------------------


@dataclass
class Construido:
    """Los bytes del libro y lo que el generador sabe de él (filas y valores guardados)."""

    datos: bytes
    filas_apu: dict[str, FilasApu]
    valores_apu: dict[str, ValoresApu]
    filas_partida: dict[str, int]  # hoja APU o "SIN-<n>" -> fila de PRESUPUESTO
    fila_subsiniva: int
    subsiniva: Decimal
    iva: Decimal
    total: Decimal
    hojas: tuple[str, ...]
    apus: tuple[ApuSint, ...]
    siembra: Siembra


_COLUMNAS_DESGLOSE = ("H", "I", "J", "K", "L", "M", "N", "O", "P")
_ROTULOS_DESGLOSE = ("MAT", "MO", "EQ", "TR", "CD", "ADM", "SUB", "UTI", "PU")


def construir_libro(
    apus: tuple[ApuSint, ...] = APUS_LIMPIOS, siembra: Siembra | None = None
) -> Construido:
    """Fabrica el `.xlsx` con fórmulas y valores guardados; devuelve los bytes y sus filas."""
    s = siembra or Siembra()
    p = s.parametros
    hojas: dict[str, _Hoja] = {}
    orden = ["PORTADA", "MEDICIONES", "INSUMOS"]
    for nombre in orden:
        hojas[nombre] = _Hoja(nombre)

    # PORTADA
    po = hojas["PORTADA"]
    po.anchos = {"A": 28, "B": 50}
    po.pon(1, "A", "PRESUPUESTO DE OBRA", fmt="titulo")
    po.pon(2, "A", s.obra)
    for k, (rot, val) in enumerate(
        (
            ("CLIENTE:", s.cliente),
            ("CONTRATISTA:", s.contratista),
            ("UBICACIÓN:", s.ubicacion),
            ("NORMA DE REFERENCIA:", "COVENIN 2000 (referencial)"),
            ("MONEDA:", s.moneda),
            ("FECHA:", s.fecha_texto),
        ),
        start=4,
    ):
        po.pon(k, "A", rot, fmt="encabezado")
        po.pon(k, "B", val)

    # INSUMOS
    ins = hojas["INSUMOS"]
    ins.anchos = {"B": 10, "C": 40, "D": 8, "E": 12, "F": 30}
    ins.pon(1, "B", "INSUMOS Y PARÁMETROS", fmt="titulo")
    for k, t in enumerate(("CÓDIGO", "DESCRIPCIÓN", "UNIDAD", "PRECIO (USD)", "FUENTE")):
        ins.pon(4, _letra(1 + k), t, fmt="encabezado")
    fila = 5
    for i in s.insumos:
        ins.pon(fila, "B", i.codigo)
        ins.pon(fila, "C", i.descripcion)
        ins.pon(fila, "D", i.unidad)
        ins.pon(fila, "E", i.precio, fmt="editable")
        ins.pon(fila, "F", i.fuente)
        fila += 1
    fin_insumos = fila - 1
    fila += 2
    ins.pon(fila, "B", "4. PARÁMETROS GLOBALES", fmt="seccion")
    fila += 1
    celdas_param: dict[str, str] = {}
    for nombre, valor in p.items():
        ins.pon(fila, "B", nombre)
        ins.pon(fila, "C", f"Parámetro {nombre}")
        ins.pon(fila, "E", valor, fmt="editable")
        celdas_param[nombre] = f"=INSUMOS!$E${fila}"
        fila += 1

    # APU
    filas_apu: dict[str, FilasApu] = {}
    valores_apu: dict[str, ValoresApu] = {}
    filas_partida: dict[str, int] = {}
    fila = FILA_PRIMERA_PARTIDA
    for a in apus:
        if not a.en_presupuesto:
            continue
        filas_partida[a.nombre_hoja] = fila
        fila += 1
    for ps in s.partidas_sin_apu:
        filas_partida[f"SIN-{ps.numero}"] = fila
        fila += 1
    fila_ultima = fila - 1
    for a in apus:
        h = _Hoja(a.nombre_hoja)
        hojas[a.nombre_hoja] = h
        orden.append(a.nombre_hoja)
        fpart = filas_partida.get(a.nombre_hoja)
        desc_titulo = a.descripcion
        if a.fila_titulo is not None:
            otro = next((x for x in apus if filas_partida[x.nombre_hoja] == a.fila_titulo), None)
            desc_titulo = otro.descripcion if otro else ""
        filas_apu[a.nombre_hoja], valores_apu[a.nombre_hoja] = _apu(h, a, s, fpart, desc_titulo)

    # PRESUPUESTO
    pr = _Hoja("PRESUPUESTO")
    hojas["PRESUPUESTO"] = pr
    orden.append("PRESUPUESTO")
    pr.anchos = {"B": 5, "C": 15, "D": 40, "E": 6, "F": 8, "G": 10}
    pr.pon(1, "B", "PRESUPUESTO", fmt="titulo")
    cab = ("Nº", "CÓDIGO", "DESCRIPCIÓN", "UND", "REND.", "CANTIDAD") + (
        "Materiales",
        "Mano de obra",
        "Equipos",
        "Transporte",
        "Costo directo",
        "Admón.",
        "Sub-total",
        "Utilidad",
        "P.U.",
        "MONTO",
        "VERIF.",
        "PESO",
    )
    for k, t in enumerate(cab):
        pr.pon(3, _letra(1 + k), t, fmt="encabezado")
    pr.pon(4, "B", "CAPÍTULO 1. OBRAS DE ALBAÑILERÍA (FICTICIAS)", fmt="seccion")
    montos: list[Decimal] = []
    fila_sub = fila_ultima + 1
    fila_tot = fila_sub + 2
    fila_iva = fila_tot + 1
    fila_gen = fila_iva + 1
    for a in apus:
        if not a.en_presupuesto:
            continue
        f = filas_partida[a.nombre_hoja]
        fa = filas_apu[a.nombre_hoja]
        va = valores_apu[a.nombre_hoja]
        hoja_a = a.nombre_hoja
        por_numero = hoja_a == f"APU-{a.numero:02d}"
        pr.pon(f, "B", Decimal(a.numero), fmt="entero")
        pr.pon(f, "C", a.codigo)
        pr.pon(f, "D", a.descripcion)
        pr.pon(f, "E", a.unidad)

        def lee(celda: str, f: int = f, hoja_a: str = hoja_a, por_numero: bool = por_numero) -> str:
            if por_numero:
                return f'=INDIRECT("\'APU-"&TEXT($B{f},"00")&"\'!{celda}")'
            return f"={_q(hoja_a)}!{celda}"

        fr = s.rend_fila_fija or fa.rend
        # Valor guardado = lo que hay en la celda leída (el libro estaba recalculado), salvo que se
        # siembre un valor viejo (L3).
        leido = _valor_en(hojas[hoja_a], fr, "F")
        rend_g = s.rend_guardado.get(a.numero, leido if isinstance(leido, Decimal) else None)
        pr.pon(f, "F", rend_g, formula=lee(f"F{fr}"), fmt="numero")
        pr.pon(f, "G", a.cantidad, fmt="editable")
        filas_r = {
            "MAT": fa.mat_r,
            "MO": fa.mo_r,
            "EQ": fa.eq_r,
            "TR": fa.tr_r,
            "CD": fa.cd,
            "ADM": fa.adm,
            "SUB": fa.sub,
            "UTI": fa.uti,
            "PU": fa.pu,
        }
        for col, rot in zip(_COLUMNAS_DESGLOSE, _ROTULOS_DESGLOSE, strict=True):
            valor = getattr(va, rot)
            fila_leida = filas_r[rot]
            if rot == "PU" and s.p_fila_fija is not None:
                fila_leida = s.p_fila_fija
                valor = _valor_en(hojas[hoja_a], fila_leida, "G")
            if rot == "PU" and a.numero in s.p_guardado:
                valor = s.p_guardado[a.numero]
            if rot == "CD" and a.numero in s.desglose_delta:
                valor = valor + s.desglose_delta[a.numero]
            pr.pon(f, col, valor, formula=lee(f"G{fila_leida}"))
        p_val = pr.v(f, "P")
        n_val, o_val = pr.v(f, "N"), pr.v(f, "O")
        verif = s.verificacion.get(a.numero, p_val - n_val - o_val)
        monto = a.cantidad * p_val
        montos.append(monto)
        pr.pon(f, "Q", monto, formula=f"=G{f}*P{f}", fmt="total_num")
        pr.pon(f, "R", verif, formula=f"=P{f}-N{f}-O{f}")
    for ps in s.partidas_sin_apu:
        f = filas_partida[f"SIN-{ps.numero}"]
        pr.pon(f, "B", Decimal(ps.numero), fmt="entero")
        pr.pon(f, "C", ps.codigo)
        pr.pon(f, "D", ps.descripcion)
        pr.pon(f, "E", ps.unidad)
        pr.pon(f, "G", ps.cantidad, fmt="editable")
        pr.pon(f, "P", ps.precio, fmt="editable")
        monto = ps.cantidad * ps.precio
        montos.append(monto)
        pr.pon(f, "Q", monto, formula=f"=G{f}*P{f}", fmt="total_num")
    subtotal = sum(montos, Decimal(0))
    for f in range(FILA_PRIMERA_PARTIDA, fila_ultima + 1):
        if (f, "Q") in pr.celdas:
            pr.pon(f, "S", pr.v(f, "Q") / subtotal, formula=f"=Q{f}/SUBSINIVA", fmt="porcentaje")
    pr.pon(fila_sub, "B", "SUBTOTAL CAPÍTULO 1", fmt="subtotal")
    pr.pon(
        fila_sub,
        "Q",
        subtotal,
        formula=f"=SUM(Q{FILA_PRIMERA_PARTIDA}:Q{fila_ultima})",
        fmt="subtotal_num",
    )
    pr.pon(fila_tot, "B", "TOTAL COSTO DE LA OBRA (SUB-TOTAL SIN IVA)", fmt="total")
    pr.pon(fila_tot, "Q", subtotal, formula=f"=Q{fila_sub}", fmt="total_num")
    iva = subtotal * p["IVA"]
    pr.pon(fila_iva, "B", "IVA 16 %", fmt="subtotal")
    pr.pon(fila_iva, "Q", iva, formula=f"=Q{fila_tot}*IVA", fmt="subtotal_num")
    total = subtotal + iva
    pr.pon(fila_gen, "B", "TOTAL PRESUPUESTO (USD)", fmt="total")
    pr.pon(fila_gen, "Q", total, formula=f"=Q{fila_tot}+Q{fila_iva}", fmt="total_num")

    # RESUMEN
    re_ = _Hoja("RESUMEN")
    hojas["RESUMEN"] = re_
    orden.append("RESUMEN")
    re_.anchos = {"A": 36, "B": 16}
    re_.pon(1, "A", "RESUMEN DEL PRESUPUESTO", fmt="titulo")
    re_.pon(3, "A", "COMPOSICIÓN DEL COSTO", fmt="encabezado")
    rango_g = f"PRESUPUESTO!$G${FILA_PRIMERA_PARTIDA}:$G${fila_ultima}"
    comp = Decimal(0)
    filas_comp = (
        ("Materiales", "H", "MAT"),
        ("Mano de obra", "I", "MO"),
        ("Equipos y herramientas", "J", "EQ"),
        ("Transporte y disposición", "K", "TR"),
        ("Administración", "M", "ADM"),
        ("Utilidad", "O", "UTI"),
    )
    for k, (texto, col, _rot) in enumerate(filas_comp, start=4):
        v = sum(
            (
                pr.v(f, "G") * pr.v(f, col)
                for f in range(FILA_PRIMERA_PARTIDA, fila_ultima + 1)
                if isinstance(pr.v(f, col), Decimal)
            ),
            Decimal(0),
        )
        comp += v
        re_.pon(
            k,
            "A",
            texto,
        )
        re_.pon(
            k,
            "B",
            v,
            formula=f"=SUMPRODUCT({rango_g},PRESUPUESTO!${col}${FILA_PRIMERA_PARTIDA}:${col}${fila_ultima})",
        )
    re_.pon(10, "A", "Total composición del costo", fmt="subtotal")
    re_.pon(10, "B", comp + s.resumen_composicion_delta, formula="=SUM(B4:B9)", fmt="subtotal_num")
    re_.pon(12, "A", "CAPÍTULO 1. OBRAS DE ALBAÑILERÍA (FICTICIAS)")
    re_.pon(12, "B", subtotal, formula=f"=PRESUPUESTO!Q{fila_sub}")
    fin_cap = 12
    if s.resumen_ref_rota:
        re_.pon(13, "A", "CAPÍTULO 2. BORRADO")
        re_.pon(13, "B", "#REF!", formula="=PRESUPUESTO!#REF!")
        fin_cap = 13
    re_.pon(15, "A", "Costo de la obra (sin IVA)", fmt="total")
    re_.pon(15, "B", subtotal, formula=f"=SUM(B12:B{fin_cap})", fmt="total_num")

    # MEDICIONES
    me = hojas["MEDICIONES"]
    me.anchos = {"A": 30, "B": 10, "C": 10, "D": 12}
    me.pon(1, "A", "MEDICIONES", fmt="titulo")
    me.pon(3, "A", "A · Frisos", fmt="seccion")
    me.pon(4, "A", "Pared norte")
    me.pon(4, "B", D("9.73"), fmt="editable")
    me.pon(4, "C", D("2.75"), fmt="editable")
    me.pon(4, "D", D("9.73") * D("2.75"), formula="=B4*C4")
    fila = 5
    for k, texto in enumerate(s.mediciones_literales, start=1):
        me.pon(fila, "A", f"Medida sembrada {k}")
        me.pon(fila, "D", _evaluar_literal(texto), formula=texto)
        fila += 1
    if s.formula_externa:
        me.pon(fila, "A", "Medida de otro libro")
        me.pon(fila, "D", D("1"), formula="=[1]Hoja1!$A$1")
        fila += 1

    # CRONOGRAMA
    cr = _Hoja("CRONOGRAMA")
    hojas["CRONOGRAMA"] = cr
    orden.append("CRONOGRAMA")
    cr.anchos = {"A": 5, "B": 36, "C": 10, "D": 12, "E": 12}
    cr.pon(1, "A", "CRONOGRAMA", fmt="titulo")
    cr.pon(2, "A", "Días laborables por semana")
    cr.pon(2, "C", D("5"), fmt="editable")
    for k, t in enumerate(("Nº", "Partida", "Cantidad", "Rendimiento", "Duración (días)")):
        cr.pon(3, _letra(k), t, fmt="encabezado")
    fila = 4
    for a in apus:
        if not a.en_presupuesto:
            continue
        fp = filas_partida[a.nombre_hoja]
        fa = filas_apu[a.nombre_hoja]
        cr.pon(fila, "A", Decimal(a.numero), fmt="entero")
        cr.pon(fila, "B", a.descripcion, formula=f"=PRESUPUESTO!D{fp}")
        cr.pon(fila, "C", a.cantidad, formula=f"=PRESUPUESTO!G{fp}")
        fr = s.cronograma_fila_rend or fa.rend
        rend = _valor_en(hojas[a.nombre_hoja], fr, "F")
        rend_v = rend if isinstance(rend, Decimal) else Decimal(0)
        if a.nombre_hoja == f"APU-{a.numero:02d}":
            f_rend = f'=INDIRECT("\'APU-"&TEXT($A{fila},"00")&"\'!F{fr}")'
        else:
            f_rend = f"={_q(a.nombre_hoja)}!F{fr}"
        cr.pon(fila, "D", rend_v, formula=f_rend)
        dur = a.cantidad / rend_v if rend_v else Decimal(0)
        cr.pon(fila, "E", dur, formula=f"=IF(D{fila}=0,0,C{fila}/D{fila})")
        fila += 1

    # PROCURA
    pc = _Hoja("PROCURA")
    hojas["PROCURA"] = pc
    orden.append("PROCURA")
    pc.anchos = {"A": 40, "B": 16}
    pc.pon(1, "A", "PROCURA — LISTA DE COMPRAS", fmt="titulo")
    total_mat = re_.v(4, "B")
    pc.pon(4, "A", "Total materiales según la lista")
    pc.pon(4, "B", total_mat + s.procura_dif, fmt="editable")
    pc.pon(5, "A", "Dif. vs presupuesto materiales")
    pc.pon(5, "B", s.procura_dif, formula="=B4-RESUMEN!B4")
    pc.pon(6, "A", "Dif. vs Costo Directo")
    pc.pon(
        6, "B", s.procura_dif + s.procura_dif_solo_total, formula=f"=B5+{s.procura_dif_solo_total}"
    )

    # PLAN DE PAGOS
    pp = _Hoja("PLAN DE PAGOS")
    hojas["PLAN DE PAGOS"] = pp
    orden.append("PLAN DE PAGOS")
    pp.anchos = {"A": 30, "B": 16}
    pp.pon(1, "A", "PLAN DE PAGOS", fmt="titulo")
    pp.pon(3, "A", "Anticipo")
    pp.pon(3, "B", D("0.3"), fmt="editable")
    pp.pon(4, "A", "Total del presupuesto")
    pp.pon(4, "B", total, formula="=TOTALGEN")
    pp.pon(5, "A", "Suma de los pagos")
    # Anticipo + resto sobre el total (como los porcentajes de la plantilla); `plan_dif` siembra un
    # pago que no cuadra (H7 en PLAN DE PAGOS).
    pp.pon(
        5,
        "B",
        total * D("0.3") + total * (1 - D("0.3")) + s.plan_dif,
        formula=f"=B4*B3+B4*(1-B3)+{s.plan_dif}",
    )
    pp.pon(6, "A", "Verificación (debe ser 0)")
    pp.pon(6, "B", s.plan_dif, formula="=B5-B4")

    # AUX
    ax = _Hoja("AUX")
    hojas["AUX"] = ax
    orden.append("AUX")
    ax.pon(1, "A", "ESCOMBRO POR PARTIDA")
    fila = 2
    for a in apus:
        fa = filas_apu[a.nombre_hoja]
        if not a.en_presupuesto:
            continue
        if fa.esc is None and a.numero not in s.aux_escombro_celda:
            continue
        celda = s.aux_escombro_celda.get(a.numero, f"G{fa.esc}")
        ax.pon(fila, "A", a.nombre_hoja)
        v = _valor_en(hojas[a.nombre_hoja], int(celda[1:]), celda[0])
        ax.pon(
            fila,
            "B",
            v if isinstance(v, Decimal) else Decimal(0),
            formula=f"={_q(a.nombre_hoja)}!{celda}",
        )
        fila += 1

    # Nombres definidos
    nombres: dict[str, str] = {}
    for nombre, ref in celdas_param.items():
        if nombre not in s.sin_parametros:
            nombres[nombre] = ref
    nombres["PRECIOS"] = f"=INSUMOS!$B$5:$F${fin_insumos}"
    nombres["SUBSINIVA"] = f"=PRESUPUESTO!$Q${fila_tot}"
    nombres["IVATOT"] = f"=PRESUPUESTO!$Q${fila_iva}"
    nombres["TOTALGEN"] = f"=PRESUPUESTO!$Q${fila_gen}"
    for k, n in enumerate(s.nombres_externos, start=1):
        nombres[n] = f"='[1]Mediciones'!$A${k}"
    for n in s.nombres_rotos:
        nombres[n] = "=#REF!"

    for clave_celda, (valor, formula) in s.parches.items():
        hoja, ref = clave_celda.split("!", 1)
        letras = ref.rstrip("0123456789")
        hojas[hoja].pon(int(ref[len(letras) :]), letras, valor, formula=formula)

    datos = _escribir(hojas, orden, nombres, s)
    if s.vinculo_externo is not None:
        datos = _con_vinculo_externo(datos, s.vinculo_externo)
    return Construido(
        datos=datos,
        filas_apu=filas_apu,
        valores_apu=valores_apu,
        filas_partida=filas_partida,
        fila_subsiniva=fila_tot,
        subsiniva=subtotal,
        iva=iva,
        total=total,
        hojas=tuple(orden),
        apus=apus,
        siembra=s,
    )


def _valor_en(h: _Hoja, fila: int, col: str) -> Any:
    return h.v(fila, col)


def _evaluar_literal(texto: str) -> Decimal:
    """Valor de una fórmula de solo literales y `*` (las de MEDICIONES sembradas)."""
    t = texto.lstrip("=")
    if "*" in t:
        a, b = t.split("*", 1)
        if a.replace(".", "").isdigit() and b.replace(".", "").isdigit():
            return Decimal(a) * Decimal(b)
    return Decimal(0)


# --- Escritura con XlsxWriter ---------------------------------------------------------------------


def _formatos(wb: Any) -> dict[str, Any]:
    base = {"font_name": "Arial", "font_size": 9, "font_color": "#" + PALETA["texto"]}

    def f(**kw: Any) -> Any:
        return wb.add_format({**base, **kw})

    blanco = "#" + PALETA["blanco"]
    return {
        "texto": f(),
        "numero": f(num_format="#,##0.00"),
        "entero": f(num_format="0"),
        "porcentaje": f(num_format="0.00%"),
        "titulo": f(bold=True, font_color=blanco, bg_color="#" + PALETA["titulo"], font_size=11),
        "subtitulo": f(bold=True),
        "encabezado": f(bold=True, font_color=blanco, bg_color="#" + PALETA["encabezado"]),
        "seccion": f(bold=True, font_color="#" + PALETA["titulo"]),
        "subtotal": f(bold=True, bg_color="#" + PALETA["subtotal"]),
        "subtotal_num": f(bold=True, bg_color="#" + PALETA["subtotal"], num_format="#,##0.00"),
        "editable": f(bg_color="#" + PALETA["editable"], num_format="#,##0.00##"),
        "total": f(bold=True, bg_color="#" + PALETA["total"]),
        "total_num": f(bold=True, bg_color="#" + PALETA["total"], num_format="#,##0.00"),
        "nota": f(italic=True),
    }


def _escribir(
    hojas: Mapping[str, _Hoja], orden: list[str], nombres: Mapping[str, str], s: Siembra
) -> bytes:
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "strings_to_numbers": False})
    wb.set_properties({"author": s.autor, "title": "Libro sintético ficticio"})
    fm = _formatos(wb)
    for nombre in orden:
        h = hojas[nombre]
        ws = wb.add_worksheet(nombre)
        for col, ancho in h.anchos.items():
            ws.set_column(f"{col}:{col}", ancho)
        for (fila, col), c in sorted(h.celdas.items(), key=lambda x: (x[0][0], _col(x[0][1]))):
            r, k = fila - 1, _col(col)
            fmt = fm.get(c.formato, fm["texto"])
            if c.formula is not None:
                v = c.valor
                if isinstance(v, Decimal):
                    v = float(v)
                elif v is None:
                    v = ""
                ws.write_formula(r, k, c.formula, fmt, v)
            elif isinstance(c.valor, Decimal):
                ws.write_number(r, k, float(c.valor), fmt)
            elif c.valor is None:
                ws.write_blank(r, k, None, fmt)
            else:
                ws.write_string(r, k, str(c.valor), fmt)
    for nombre, ref in nombres.items():
        wb.define_name(nombre, ref)
    wb.close()
    return buf.getvalue()


def _con_vinculo_externo(datos: bytes, destino: str) -> bytes:
    """Añade la pieza de un vínculo a otro libro (`xl/externalLinks/_rels/...rels`), como la que
    Excel deja al copiar una hoja desde un libro en la red (H11, causa C5)."""
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        f'relationships/externalLinkPath" Target="{destino}" TargetMode="External"/>'
        "</Relationships>"
    )
    enlace = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<externalLink xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<externalBook xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships" r:id="rId1"/></externalLink>'
    )
    entrada = io.BytesIO(datos)
    salida = io.BytesIO()
    with (
        zipfile.ZipFile(entrada) as zin,
        zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr("xl/externalLinks/externalLink1.xml", enlace)
        zout.writestr("xl/externalLinks/_rels/externalLink1.xml.rels", rels)
    return salida.getvalue()


# --- Atajos ---------------------------------------------------------------------------------------


def libro_limpio() -> Construido:
    """El libro limpio, contrastado contra la memoria de cálculo a mano (`MEMORIA`)."""
    c = construir_libro()
    for hoja, esperados in MEMORIA["componentes"].items():
        v = c.valores_apu[hoja]
        for rot, esperado in esperados.items():
            obtenido = getattr(v, rot)
            if obtenido != esperado:
                raise AssertionError(f"generador ≠ memoria: {hoja} {rot} {obtenido} ≠ {esperado}")
    for clave_ in ("SUBSINIVA",):
        if c.subsiniva != MEMORIA[clave_]:
            raise AssertionError(f"generador ≠ memoria: {clave_} {c.subsiniva}")
    if c.iva != MEMORIA["IVATOT"] or c.total != MEMORIA["TOTALGEN"]:
        raise AssertionError("generador ≠ memoria: IVA o total")
    return c


def con(apu: ApuSint, **cambios: Any) -> ApuSint:
    """Copia de un APU con cambios (atajo para sembrar)."""
    return replace(apu, **cambios)
