# core/budget/reajuste.py (parte pura; la Tarea 12 agrega guardar_estudio y cargar_estudio)
"""SL-E3: reajuste por fórmula escalatoria y por comprobación directa (UC-18; S1 §8). Supuestos
declarados, todo «a cotejar con la Gaceta»: Vpm = Vo·(Km−1)·(1−R) es INDICIO (S1-R8); índice del mes
de cierre (S1-R10); primer año solo en contratos > 12 meses (S1-R9); R no se aplica a la
comprobación salvo declaración (S1-R14); reconocido por `mecanismo_pagadero` (S1-R20); mes en curso
«parcial al corte» (S1-R21). Funciones puras, 28 dígitos y ROUND_HALF_EVEN."""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum

from core.catalog.moneda import convertir
from core.contracts.apu import ResultadoAPU

COMPONENTES = ("materiales", "equipos", "mano_obra")
CERO = Decimal(0)
MARCA_PRIMER_ANIO = "precios fijos el primer año (art. 134, a cotejar)"
MARCA_EXCEPCION = "excepción declarada"
MARCA_PROVISIONAL = "provisional"
MARCA_INDICE_FALTANTE = "índice faltante: período no calculado"
MARCA_SIN_COMPROBACION = "comprobación no disponible"
MARCA_SIN_RECONOCIDO = "sin monto reconocido: el mecanismo reconocido no está disponible"
AVISO_USD_BS = (
    "ADVERTENCIA: proyecto en USD con un índice en bolívares: cuenta dos veces la "
    "devaluación (S1-R11)"
)
NOTA_COMISION = (
    "INDICIO: los reajustes superan el 10 % del monto original; la Comisión de "
    "Contrataciones opina sobre esas variaciones (artículo sin confirmar)"
)
NOTA_RECONSIDERACION = (
    "la escalatoria en reconsideraciones solo vale para obras y servicios "
    "(art. 134, transcripción, a cotejar)"
)


class Mecanismo(StrEnum):
    ESCALATORIA = "escalatoria"
    COMPROBACION = "comprobacion"
    AMBOS = "ambos"


class Estructura(StrEnum):
    POR_PARTIDA = "por_partida"
    DECLARADA = "declarada"


class EstadoEstudio(StrEnum):
    CERRADO = "cerrado"
    PARCIAL = "parcial al corte"


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class Componente:
    componente: str
    serie: str
    peso: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Clausula:
    fecha_inicio: date
    duracion_meses: int
    fecha_referencia_primer_anio: date
    periodicidad: str
    mecanismo: Mecanismo
    estructura: Estructura
    componentes: tuple[Componente, ...]
    fecha_base_indices: date
    r: Decimal
    fuente_r: str
    fuente: str
    responsable: str
    mecanismo_pagadero: Mecanismo | None = None
    fuente_pagadero: str = ""
    r_en_comprobacion: bool = False

    def __post_init__(self) -> None:
        if self.duracion_meses <= 0:
            raise ValueError("la duracion del contrato debe ser positiva")
        if self.fecha_base_indices.day != 1:
            raise ValueError("el mes base de los indices se declara con su primer dia (S1-R10)")
        if not (CERO <= self.r < 1) or not self.fuente_r.strip():
            raise ValueError("R va en [0, 1) con su fuente (S1-R8)")
        if not self.fuente.strip() or not self.responsable.strip():
            raise ValueError("la clausula exige fuente y responsable")
        if self.mecanismo_pagadero is not None and (
            self.mecanismo is not Mecanismo.AMBOS
            or self.mecanismo_pagadero is Mecanismo.AMBOS
            or not self.fuente_pagadero.strip()
        ):
            raise ValueError("mecanismo_pagadero solo con 'ambos', uno de los dos y con su fuente")
        nombres = [c.componente for c in self.componentes]
        if len(set(nombres)) != len(nombres):
            raise ValueError("componente repetido en la clausula")
        if self.estructura is Estructura.POR_PARTIDA:
            if sorted(nombres) != sorted(COMPONENTES):
                raise ValueError("por_partida exige materiales, equipos y mano_obra con su serie")
        else:
            if any(c.peso is None for c in self.componentes):
                raise ValueError("la estructura declarada exige el peso de cada componente")
            suma = sum((c.peso for c in self.componentes), CERO)
            if suma != 1:
                raise ValueError(f"los pesos de la estructura declarada suman {suma}, no 1 (§8.1)")


@dataclass(frozen=True, slots=True)
class PartidaContrato:
    codigo: str
    pu: Decimal
    resultado: ResultadoAPU
    presupuestado: Decimal


@dataclass(frozen=True, slots=True)
class Ejecutado:
    codigo: str
    cantidad: Decimal
    fuente: str

    def __post_init__(self) -> None:
        if self.cantidad < 0:
            raise ValueError(f"la cantidad ejecutada de {self.codigo} no puede ser negativa")


@dataclass(frozen=True, slots=True)
class PeriodoDeclarado:
    desde: date
    hasta: date
    ejecutado: tuple[Ejecutado, ...]
    version_comprobacion: str = ""
    excepcion: str = ""


@dataclass(frozen=True, slots=True)
class Comparacion:
    moneda: str
    otra: str
    tasa: Decimal | None
    escalatoria: Decimal | None
    comprobacion: Decimal | None
    diferencia: Decimal | None
    escalatoria_otra: Decimal | None
    comprobacion_otra: Decimal | None
    diferencia_otra: Decimal | None


@dataclass(frozen=True, slots=True)
class ResultadoPeriodo:
    desde: date
    hasta: date
    reajustables: Mapping[str, Decimal]
    excesos: tuple[str, ...]
    km: Decimal | None
    coeficientes: Mapping[str, Decimal]
    escalatoria: Decimal | None
    comprobacion: Decimal | None
    reconocido: Decimal | None
    mecanismo_reconocido: str
    importaciones: Mapping[str, int]
    marcas: tuple[str, ...]
    comparacion: Comparacion
    version_comprobacion: str


@dataclass(frozen=True, slots=True)
class ResultadoEstudio:
    moneda: str
    periodos: tuple[ResultadoPeriodo, ...]
    total_escalatoria: Decimal
    total_comprobacion: Decimal
    total_reconocido: Decimal
    estado: EstadoEstudio
    fecha_corte: date | None
    avisos: tuple[str, ...]


def coeficiente(pesos, base, periodo) -> Decimal:
    with _contexto():
        return sum((pesos[c] * periodo[c] / base[c] for c in pesos), CERO)


def coeficiente_de_partida(resultado: ResultadoAPU, base, periodo) -> Decimal:
    if resultado.costo_directo <= 0:
        raise ValueError("una partida con costo directo cero no tiene pesos por componente")
    montos = dict(
        zip(
            COMPONENTES, (resultado.materiales, resultado.equipos, resultado.mano_obra), strict=True
        )
    )
    with _contexto():
        return (
            sum((montos[c] * periodo[c] / base[c] for c in COMPONENTES), CERO)
            / resultado.costo_directo
        )


def reajuste_escalatorio(clausula, contrato, reajustables, base, periodo) -> Decimal:
    with _contexto():
        if clausula.estructura is Estructura.DECLARADA:
            pesos = {c.componente: c.peso for c in clausula.componentes}
            vo = sum((q * contrato[c].pu for c, q in reajustables.items()), CERO)
            return vo * (coeficiente(pesos, base, periodo) - 1) * (1 - clausula.r)
        return sum(
            (
                q
                * contrato[c].pu
                * (coeficiente_de_partida(contrato[c].resultado, base, periodo) - 1)
                * (1 - clausula.r)
                for c, q in reajustables.items()
            ),
            CERO,
        )


def reajuste_por_comprobacion(reajustables, pu_contrato, pu_comprobado, r=CERO) -> Decimal:
    with _contexto():
        return sum(
            (q * (pu_comprobado[c] - pu_contrato[c]) for c, q in reajustables.items()), CERO
        ) * (1 - r)


def comparar_reajustes(escalatoria, comprobacion, *, moneda, tasa) -> Comparacion:
    otra = "USD" if moneda == "Bs" else "Bs"
    diferencia = None if escalatoria is None or comprobacion is None else escalatoria - comprobacion

    def a_otra(x):
        return None if x is None or tasa is None else convertir(x, moneda, otra, tasa)

    return Comparacion(
        moneda,
        otra,
        tasa,
        escalatoria,
        comprobacion,
        diferencia,
        a_otra(escalatoria),
        a_otra(comprobacion),
        a_otra(diferencia),
    )


def _aniversario(d: date) -> date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:  # 29 de febrero
        return date(d.year + 1, 3, 1)


def _reajustables(contrato, periodos):
    acumulado = dict.fromkeys(contrato, CERO)
    for periodo in periodos:
        cantidades, excesos = {}, []
        for e in periodo.ejecutado:
            if e.codigo not in contrato:
                raise ValueError(f"la partida {e.codigo} no esta en la version del contrato")
            disponible = max(CERO, contrato[e.codigo].presupuestado - acumulado[e.codigo])
            if e.cantidad > disponible:
                excesos.append(e.codigo)
            cantidades[e.codigo] = cantidades.get(e.codigo, CERO) + min(e.cantidad, disponible)
            acumulado[e.codigo] += e.cantidad
        yield cantidades, tuple(dict.fromkeys(excesos))


def calcular_estudio(
    clausula,
    contrato,
    periodos,
    indices,
    *,
    moneda,
    tasas,
    pu_comprobados,
    monto_original,
    fecha_calculo,
    series_en_bs=frozenset(),
) -> ResultadoEstudio:
    periodos = list(periodos)
    if not periodos:
        raise ValueError("el estudio necesita al menos un periodo")
    if any(p.desde > p.hasta for p in periodos) or any(
        a.hasta >= b.desde for a, b in zip(periodos, periodos[1:], strict=False)
    ):
        raise ValueError("los periodos van en orden y sin solaparse")
    aniversario = _aniversario(clausula.fecha_referencia_primer_anio)
    resultados = []
    for periodo, (cantidades, excesos), tasa, comprobado in zip(
        periodos, _reajustables(contrato, periodos), tasas, pu_comprobados, strict=True
    ):
        marcas: list[str] = []
        if excesos:
            marcas.append(
                "ejecutado mayor que lo presupuestado: se reajusta hasta lo presupuestado"
            )
        congelado = False
        if clausula.duracion_meses > 12:
            if periodo.desde < aniversario <= periodo.hasta:
                raise ValueError(
                    f"el periodo {periodo.desde}–{periodo.hasta} cruza el aniversario "
                    f"{aniversario}: partalo (UC-18 3b)"
                )
            if periodo.hasta < aniversario:
                congelado = not periodo.excepcion.strip()
                marcas.append(MARCA_EXCEPCION if not congelado else MARCA_PRIMER_ANIO)
        mes = date(periodo.hasta.year, periodo.hasta.month, 1)
        base, actual, citas, provisional, km, coefs = {}, {}, {}, False, None, {}
        for comp in clausula.componentes:
            i0, im = (
                indices.get((comp.serie, clausula.fecha_base_indices)),
                indices.get((comp.serie, mes)),
            )
            if i0 is None or im is None:
                base = None
                break
            base[comp.componente], actual[comp.componente] = i0.valor, im.valor
            citas[f"{comp.serie}@{i0.fecha.isoformat()}"] = i0.importacion_id
            citas[f"{comp.serie}@{im.fecha.isoformat()}"] = im.importacion_id
            provisional = provisional or i0.provisional or im.provisional
        if congelado:
            escalatoria = CERO
        elif base is None:
            escalatoria = None
            marcas.append(MARCA_INDICE_FALTANTE)
        else:
            escalatoria = reajuste_escalatorio(clausula, contrato, cantidades, base, actual)
            if clausula.estructura is Estructura.DECLARADA:
                km = coeficiente({c.componente: c.peso for c in clausula.componentes}, base, actual)
            else:
                coefs = {
                    c: coeficiente_de_partida(contrato[c].resultado, base, actual)
                    for c in cantidades
                }
        if provisional:
            marcas.append(MARCA_PROVISIONAL)
        if congelado:
            comprobacion = CERO
        elif comprobado is None:
            comprobacion = None
            marcas.append(MARCA_SIN_COMPROBACION)
        else:
            comprobacion = reajuste_por_comprobacion(
                cantidades,
                {c: p.pu for c, p in contrato.items()},
                comprobado,
                clausula.r if clausula.r_en_comprobacion else CERO,
            )
        elegido = (
            clausula.mecanismo
            if clausula.mecanismo is not Mecanismo.AMBOS
            else clausula.mecanismo_pagadero or Mecanismo.ESCALATORIA
        )
        reconocido = escalatoria if elegido is Mecanismo.ESCALATORIA else comprobacion
        if reconocido is None:
            marcas.append(MARCA_SIN_RECONOCIDO)
        resultados.append(
            ResultadoPeriodo(
                periodo.desde,
                periodo.hasta,
                cantidades,
                excesos,
                km,
                coefs,
                escalatoria,
                comprobacion,
                reconocido,
                elegido.value,
                citas,
                tuple(marcas),
                comparar_reajustes(escalatoria, comprobacion, moneda=moneda, tasa=tasa),
                periodo.version_comprobacion,
            )
        )

    def total(campo: str) -> Decimal:
        return sum((getattr(r, campo) for r in resultados if getattr(r, campo) is not None), CERO)

    avisos = [NOTA_RECONSIDERACION]
    if moneda == "USD" and any(c.serie in series_en_bs for c in clausula.componentes):
        avisos.append(AVISO_USD_BS)
    with _contexto():
        if monto_original and total("reconocido") / monto_original > Decimal("0.10"):
            avisos.append(NOTA_COMISION)
    ultimo = periodos[-1].hasta
    fin = date(ultimo.year, ultimo.month, calendar.monthrange(ultimo.year, ultimo.month)[1])
    estado = EstadoEstudio.PARCIAL if fecha_calculo < fin else EstadoEstudio.CERRADO
    return ResultadoEstudio(
        moneda,
        tuple(resultados),
        total("escalatoria"),
        total("comprobacion"),
        total("reconocido"),
        estado,
        fecha_calculo if estado is EstadoEstudio.PARCIAL else None,
        tuple(avisos),
    )
