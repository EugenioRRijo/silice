"""SL-E3: reajuste por fórmula escalatoria y por comprobación directa (UC-18; S1 §8). Supuestos
declarados, todo «a cotejar con la Gaceta»: Vpm = Vo·(Km−1)·(1−R) es INDICIO (S1-R8); índice del mes
de cierre (S1-R10); primer año solo en contratos > 12 meses (S1-R9); R no se aplica a la
comprobación salvo declaración (S1-R14); reconocido por `mecanismo_pagadero` (S1-R20); mes en curso
«parcial al corte» (S1-R21). Funciones puras, 28 dígitos y ROUND_HALF_EVEN."""

from __future__ import annotations

import calendar
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.indices import (
    LADO_POR_DEFECTO,
    UNIDAD_INDICE_BS,
    TasaNoDisponible,
    ValorFechado,
    tasa_aplicable,
    valor_en,
)
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


@dataclass(frozen=True, slots=True)
class EstudioCargado:
    """Un estudio recargado: sus entradas reconstruidas y su resultado recalculado, que es igual al
    guardado (si no, `cargar_estudio` no lo devuelve)."""

    id: int
    version_id: int
    estado: EstadoEstudio
    reemplaza_a: int | None
    clausula: Clausula
    periodos: tuple[PeriodoDeclarado, ...]
    resultado: ResultadoEstudio


def contrato_de_version(version: models.Presupuesto) -> dict[str, PartidaContrato]:
    contrato: dict[str, PartidaContrato] = {}
    for r in version.partidas:
        codigo = r.partida.codigo
        resultado = ResultadoAPU(
            r.materiales,
            r.equipos,
            r.mano_obra,
            r.costo_directo,
            r.con_administracion,
            r.precio_unitario,
        )
        previo = contrato.get(codigo)
        contrato[codigo] = PartidaContrato(
            codigo,
            r.precio_unitario,
            resultado,
            r.cantidad + (previo.presupuestado if previo else CERO),
        )
    return contrato


def _series(session: Session, clausula: Clausula) -> dict[str, models.SerieIndice]:
    codigos = [c.serie for c in clausula.componentes]
    series = {
        s.codigo: s
        for s in session.scalars(
            select(models.SerieIndice).where(models.SerieIndice.codigo.in_(codigos))
        )
    }
    faltan = [codigo for codigo in codigos if codigo not in series]
    if faltan:
        raise ValueError(f"las series {', '.join(faltan)} no estan importadas (UC-17)")
    return series


def _mes_de_cierre(periodo: PeriodoDeclarado) -> date:
    return date(periodo.hasta.year, periodo.hasta.month, 1)


def _indices_vigentes(
    session: Session, clausula: Clausula, periodos: Sequence[PeriodoDeclarado]
) -> dict[tuple[str, date], ValorFechado]:
    """El valor de cada serie en el mes base y en el mes de cierre de cada período, de la
    importación vigente al calcular (S1-R10). Lo que no está queda fuera: el período se declara
    sin calcular."""
    fechas = {clausula.fecha_base_indices, *(_mes_de_cierre(p) for p in periodos)}
    indices: dict[tuple[str, date], ValorFechado] = {}
    for componente in clausula.componentes:
        for fecha in fechas:
            valor = valor_en(session, componente.serie, fecha)
            if valor is not None:
                indices[(componente.serie, fecha)] = valor
    return indices


def _version_de_comprobacion(
    session: Session, version: models.Presupuesto, codigo: str
) -> models.Presupuesto | None:
    if not codigo.strip():
        return None
    otra = session.scalars(
        select(models.Presupuesto).where(
            models.Presupuesto.proyecto_id == version.proyecto_id,
            models.Presupuesto.codigo == codigo.strip(),
        )
    ).one_or_none()
    if otra is None:
        raise ValueError(
            f"la version de comprobacion {codigo!r} no existe en el proyecto (UC-18 4)"
        )
    return otra


def _pu_de(
    version: models.Presupuesto | None, periodo: PeriodoDeclarado
) -> dict[str, Decimal] | None:
    """El PU de cada partida ejecutada en la versión revalorada (comprobación directa, S1 §8.4)."""
    if version is None:
        return None
    pu = {r.partida.codigo: r.precio_unitario for r in version.partidas}
    faltan = sorted({e.codigo for e in periodo.ejecutado} - set(pu))
    if faltan:
        raise ValueError(
            f"la version {version.codigo} no valora {', '.join(faltan)}: no sirve de "
            "comprobacion para ese periodo"
        )
    return pu


def _tasa_o_nada(session: Session, fecha: date, lado: str) -> ValorFechado | None:
    try:
        return tasa_aplicable(session, fecha, lado=lado)
    except TasaNoDisponible:
        return None  # la otra moneda queda «no disponible» (S1 §8.4)


def _exigir_reemplazo(
    session: Session, version: models.Presupuesto, reemplaza_a: int, resultado: ResultadoEstudio
) -> None:
    parcial = session.get(models.EstudioReajuste, reemplaza_a)
    if parcial is None or parcial.presupuesto_id != version.id:
        raise ValueError(f"el estudio {reemplaza_a} no es de la version {version.codigo}")
    if parcial.estado != EstadoEstudio.PARCIAL:
        raise ValueError(f"el estudio {reemplaza_a} esta cerrado: solo un parcial se reemplaza")
    if (
        session.scalar(
            select(models.EstudioReajuste.id).where(
                models.EstudioReajuste.reemplaza_a == reemplaza_a
            )
        )
        is not None
    ):
        raise ValueError("un parcial se reemplaza una sola vez (S1-R21)")
    if resultado.estado is not EstadoEstudio.CERRADO:
        raise ValueError("el estudio que reemplaza a un parcial debe estar cerrado (S1-R21)")


def _guardar_clausula(
    session: Session,
    version: models.Presupuesto,
    clausula: Clausula,
    series: Mapping[str, models.SerieIndice],
) -> models.ClausulaReajuste:
    fila = models.ClausulaReajuste(
        presupuesto_id=version.id,
        fecha_inicio=clausula.fecha_inicio,
        duracion_meses=clausula.duracion_meses,
        fecha_referencia_primer_anio=clausula.fecha_referencia_primer_anio,
        periodicidad=clausula.periodicidad,
        mecanismo=clausula.mecanismo.value,
        mecanismo_pagadero=(
            None if clausula.mecanismo_pagadero is None else clausula.mecanismo_pagadero.value
        ),
        fuente_pagadero=clausula.fuente_pagadero,
        estructura=clausula.estructura.value,
        fecha_base_indices=clausula.fecha_base_indices,
        r=clausula.r,
        fuente_r=clausula.fuente_r,
        r_en_comprobacion=clausula.r_en_comprobacion,
        fuente=clausula.fuente,
        responsable=clausula.responsable,
    )
    session.add(fila)
    session.flush()
    session.add_all(
        models.ComponenteClausula(
            clausula_id=fila.id,
            orden=n,
            componente=c.componente,
            serie_id=series[c.serie].id,
            peso=c.peso,
        )
        for n, c in enumerate(clausula.componentes)
    )
    session.flush()
    return fila


def guardar_estudio(
    session: Session,
    version: models.Presupuesto,
    clausula: Clausula,
    periodos: Sequence[PeriodoDeclarado],
    *,
    fecha_calculo: date,
    fuente: str,
    responsable: str,
    reemplaza_a: int | None = None,
    lado: str = LADO_POR_DEFECTO,
    ahora: datetime | None = None,
) -> models.EstudioReajuste:
    """UC-18 6: calcula el estudio con los índices vigentes, la tasa de cada cierre y la versión
    revalorada de cada período, y lo guarda con todo lo que usó (S1 §8.5). Solo agrega filas; la
    versión del contrato no cambia. Hace `flush`, no `commit`."""
    fuente, responsable = fuente.strip(), responsable.strip()
    if not fuente or not responsable:
        raise ValueError("el estudio exige fuente y responsable (UC-18 6)")
    periodos = list(periodos)
    if not periodos:
        raise ValueError("el estudio necesita al menos un periodo")
    if any(not e.fuente.strip() for p in periodos for e in p.ejecutado):
        raise ValueError("cada cantidad ejecutada exige su fuente: acta o valuacion (UC-18 2)")
    contrato = contrato_de_version(version)
    series = _series(session, clausula)
    comprobaciones = [
        _version_de_comprobacion(session, version, p.version_comprobacion) for p in periodos
    ]
    tasas = [_tasa_o_nada(session, p.hasta, lado) for p in periodos]
    resultado = calcular_estudio(
        clausula,
        contrato,
        periodos,
        _indices_vigentes(session, clausula, periodos),
        moneda=version.moneda,
        tasas=[None if t is None else t.valor for t in tasas],
        pu_comprobados=[_pu_de(v, p) for v, p in zip(comprobaciones, periodos, strict=True)],
        monto_original=sum((r.total for r in version.partidas), CERO),
        fecha_calculo=fecha_calculo,
        series_en_bs=frozenset(c for c, s in series.items() if s.unidad == UNIDAD_INDICE_BS),
    )
    if reemplaza_a is not None:
        _exigir_reemplazo(session, version, reemplaza_a, resultado)
    fila_clausula = _guardar_clausula(session, version, clausula, series)
    estudio = models.EstudioReajuste(
        presupuesto_id=version.id,
        clausula_id=fila_clausula.id,
        fecha_calculo=fecha_calculo,
        estado=resultado.estado.value,
        fecha_corte=resultado.fecha_corte,
        reemplaza_a=reemplaza_a,
        moneda=version.moneda,
        lado=lado,
        monto_original=sum((r.total for r in version.partidas), CERO),
        total_escalatoria=resultado.total_escalatoria,
        total_comprobacion=resultado.total_comprobacion,
        total_reconocido=resultado.total_reconocido,
        avisos=json.dumps(list(resultado.avisos), ensure_ascii=False),
        fuente=fuente,
        responsable=responsable,
        fecha_hora=ahora or datetime.now(),
    )
    session.add(estudio)
    session.flush()
    for orden, (periodo, calculado, comprobacion, tasa) in enumerate(
        zip(periodos, resultado.periodos, comprobaciones, tasas, strict=True)
    ):
        fila = models.PeriodoReajuste(
            estudio_id=estudio.id,
            orden=orden,
            desde=periodo.desde,
            hasta=periodo.hasta,
            km=calculado.km,
            escalatoria=calculado.escalatoria,
            comprobacion=calculado.comprobacion,
            reconocido=calculado.reconocido,
            mecanismo_reconocido=calculado.mecanismo_reconocido,
            version_comprobacion_id=None if comprobacion is None else comprobacion.id,
            tasa=None if tasa is None else tasa.valor,
            fecha_tasa=None if tasa is None else tasa.fecha,
            importaciones=json.dumps(dict(calculado.importaciones), sort_keys=True),
            marcas=json.dumps(list(calculado.marcas), ensure_ascii=False),
            excepcion=periodo.excepcion,
        )
        session.add(fila)
        session.flush()
        session.add_all(
            models.EjecutadoPeriodo(
                periodo_id=fila.id,
                orden=n,
                codigo_partida=e.codigo,
                cantidad=e.cantidad,
                fuente=e.fuente,
            )
            for n, e in enumerate(periodo.ejecutado)
        )
    session.flush()
    return estudio


def _clausula_de(session: Session, clausula_id: int) -> Clausula:
    fila = session.get(models.ClausulaReajuste, clausula_id)
    componentes = session.execute(
        select(models.ComponenteClausula, models.SerieIndice.codigo)
        .join(models.SerieIndice, models.SerieIndice.id == models.ComponenteClausula.serie_id)
        .where(models.ComponenteClausula.clausula_id == clausula_id)
        .order_by(models.ComponenteClausula.orden)
    ).all()
    return Clausula(
        fila.fecha_inicio,
        fila.duracion_meses,
        fila.fecha_referencia_primer_anio,
        fila.periodicidad,
        Mecanismo(fila.mecanismo),
        Estructura(fila.estructura),
        tuple(Componente(c.componente, codigo, c.peso) for c, codigo in componentes),
        fila.fecha_base_indices,
        fila.r,
        fila.fuente_r,
        fila.fuente,
        fila.responsable,
        mecanismo_pagadero=(
            None if fila.mecanismo_pagadero is None else Mecanismo(fila.mecanismo_pagadero)
        ),
        fuente_pagadero=fila.fuente_pagadero,
        r_en_comprobacion=fila.r_en_comprobacion,
    )


def cargar_estudio(session: Session, estudio_id: int) -> EstudioCargado:
    """Recalcula el estudio con las importaciones que **cita**, la tasa guardada de cada cierre y
    los PU de la versión de comprobación citada, con su fecha de cálculo, y exige igualdad exacta de
    escalatoria, comprobación y reconocido por período con lo guardado (RNF-14). Una revisión de
    un índice importada después no lo cambia. No escribe."""
    estudio = session.get(models.EstudioReajuste, estudio_id)
    if estudio is None:
        raise ValueError(f"no hay ningun estudio de reajuste {estudio_id}")
    version = session.get(models.Presupuesto, estudio.presupuesto_id)
    clausula = _clausula_de(session, estudio.clausula_id)
    filas = list(
        session.scalars(
            select(models.PeriodoReajuste)
            .where(models.PeriodoReajuste.estudio_id == estudio.id)
            .order_by(models.PeriodoReajuste.orden)
        )
    )
    periodos: list[PeriodoDeclarado] = []
    indices: dict[tuple[str, date], ValorFechado] = {}
    pu_comprobados: list[dict[str, Decimal] | None] = []
    for fila in filas:
        ejecutado = tuple(
            Ejecutado(e.codigo_partida, e.cantidad, e.fuente)
            for e in session.scalars(
                select(models.EjecutadoPeriodo)
                .where(models.EjecutadoPeriodo.periodo_id == fila.id)
                .order_by(models.EjecutadoPeriodo.orden)
            )
        )
        comprobacion = (
            None
            if fila.version_comprobacion_id is None
            else session.get(models.Presupuesto, fila.version_comprobacion_id)
        )
        periodo = PeriodoDeclarado(
            fila.desde,
            fila.hasta,
            ejecutado,
            "" if comprobacion is None else comprobacion.codigo,
            fila.excepcion,
        )
        periodos.append(periodo)
        pu_comprobados.append(_pu_de(comprobacion, periodo))
        for clave, importacion_id in json.loads(fila.importaciones).items():
            serie, texto = clave.rsplit("@", 1)
            fecha = date.fromisoformat(texto)
            citado = valor_en(session, serie, fecha, importacion_id=importacion_id)
            if citado is None:
                raise ValueError(
                    f"el estudio {estudio.id} cita la importacion {importacion_id} de "
                    f"{serie} al {fecha:%d/%m/%Y}, que ya no esta en la base"
                )
            indices[(serie, fecha)] = citado
    series = _series(session, clausula)
    resultado = calcular_estudio(
        clausula,
        contrato_de_version(version),
        periodos,
        indices,
        moneda=estudio.moneda,
        tasas=[fila.tasa for fila in filas],
        pu_comprobados=pu_comprobados,
        monto_original=estudio.monto_original,
        fecha_calculo=estudio.fecha_calculo,
        series_en_bs=frozenset(c for c, s in series.items() if s.unidad == UNIDAD_INDICE_BS),
    )
    for fila, calculado in zip(filas, resultado.periodos, strict=True):
        guardado = (fila.escalatoria, fila.comprobacion, fila.reconocido)
        if (calculado.escalatoria, calculado.comprobacion, calculado.reconocido) != guardado:
            raise ValueError(
                f"el periodo {fila.desde:%d/%m/%Y}-{fila.hasta:%d/%m/%Y} del estudio {estudio.id} "
                "no recalcula igual a lo guardado (RNF-14)"
            )
    return EstudioCargado(
        estudio.id,
        version.id,
        EstadoEstudio(estudio.estado),
        estudio.reemplaza_a,
        clausula,
        tuple(periodos),
        resultado,
    )
