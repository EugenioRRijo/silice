# core/budget/valor_ganado.py
"""SL-E5: valor ganado, separación del desvío de control, reproyección y alertas (spec S2 §4).

Funciones **puras** con `Decimal` (sin base de datos ni `sqlalchemy`): reciben el `EstadoObra` al
corte y devuelven resultados tipados. Las divisiones van en un contexto local de 28 dígitos con
`ROUND_HALF_EVEN`, fijado dentro de cada función (S1 §5.3); se multiplica antes de dividir y se
redondea solo al presentar. Un número de días se redondea a 12 decimales antes de tomarle el techo
(S2-R9): un resto de 28 dígitos no debe adelantar un día.

Las fórmulas de PV, EV, AC, SV, CV, SPI, CPI y EAC = BAC/CPI son **definiciones del sistema**
(S2-R11): ninguna fuente que las contenga está verificada. El EAC del sistema y la separación del
desvío son propios de este trabajo y se declaran así. Los umbrales de las alertas son
SUPUESTO_DECLARADO (`ParametrosControl`).

**Separación del desvío de control** (S2 §4.3, RV-10): plazo = SV; precio = Σ qe·(u − u');
consumo = Σ qe·u' − AC; la identidad CV = precio + consumo es exacta. Es distinta de la «diferencia
entre versiones» de S3 (el término cruzado queda aquí en el consumo, allá en el precio).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Decimal, localcontext

from core.budget.curva import PeriodoPlan
from core.budget.equilibrio import EstadoEquilibrio, PuntoEquilibrio, equilibrio
from core.contracts.presupuesto import Presupuesto, PuntoCurva
from core.contracts.verificacion import Severidad

__all__ = [
    "NATURALEZA_DECLARADA",
    "PERSPECTIVA_COSTO",
    "PERSPECTIVA_PRECIO",
    "Alerta",
    "Alertas",
    "EstadoObra",
    "Indicadores",
    "ParametrosControl",
    "PartidaControl",
    "PreciosDelCorte",
    "ProyeccionPartida",
    "Reproyeccion",
    "Separacion",
    "alertas",
    "equilibrio_proyectado",
    "fin_excede",
    "indicadores",
    "partidas_de_plan",
    "precios_por_escalatoria",
    "proyectar_partida",
    "reproyectar",
    "separar_desvio",
    "techo_de_dias",
]

PERSPECTIVA_COSTO = "costo"
PERSPECTIVA_PRECIO = "precio"
NATURALEZA_DECLARADA = "SUPUESTO_DECLARADO"
CERO = Decimal(0)
UNO = Decimal(1)
CIEN = Decimal(100)
PRECISION_DE_DIAS = Decimal("1e-12")
LIMITE_DE_PERIODOS = 10_000
_ETIQUETA = re.compile(r"^(.*?)(\d+)$")


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


def techo_de_dias(dias: Decimal) -> int:
    """El techo de un número de días hábiles, tras redondearlo a 12 decimales (S2-R9)."""
    with _contexto():
        return int(dias.quantize(PRECISION_DE_DIAS).to_integral_value(rounding=ROUND_CEILING))


@dataclass(frozen=True, slots=True)
class ParametrosControl:
    """Umbrales de las alertas (§4.5) y supuestos de las opciones (§4.6). Los valores por defecto
    son SUPUESTO_DECLARADO sin fuente, editables por proyecto con su `RegistroCambio`;
    `penalizacion_diaria` es un dato del contrato (ninguna norma verificada la fija)."""

    spi_error: Decimal = Decimal("0.90")
    cpi_error: Decimal = Decimal("0.90")
    retraso_error: Decimal = Decimal("0.10")
    precio_info: Decimal = Decimal("0.05")
    equilibrio_puntos: Decimal = Decimal("10")
    eta_cuadrilla: Decimal = Decimal("0.80")
    cuadrillas_max: int = 3
    eta_horas_extra: Decimal = Decimal("0.80")
    horas_extra_dia: Decimal = Decimal("2")
    recargo_horas_extra: Decimal = Decimal("0.50")
    fcas_en_horas_extra: bool = True
    penalizacion_diaria: Decimal = CERO
    fuente_penalizacion: str = ""

    def __post_init__(self) -> None:
        for nombre in ("eta_cuadrilla", "eta_horas_extra"):
            if not CERO < getattr(self, nombre) <= UNO:
                raise ValueError(f"{nombre} debe estar en (0, 1]: {getattr(self, nombre)}")
        if self.cuadrillas_max < 2:
            raise ValueError(f"cuadrillas_max debe ser 2 o mas: {self.cuadrillas_max}")
        for nombre in (
            "spi_error",
            "cpi_error",
            "retraso_error",
            "precio_info",
            "equilibrio_puntos",
            "horas_extra_dia",
            "recargo_horas_extra",
            "penalizacion_diaria",
        ):
            if getattr(self, nombre) < CERO:
                raise ValueError(f"{nombre} no puede ser negativo: {getattr(self, nombre)}")


@dataclass(frozen=True, slots=True)
class PartidaControl:
    """Una partida de la línea base: cantidad `q`, unitario `u` según la perspectiva y la fracción
    del plan en cada período (`plan[n-1]` es la del período `n`)."""

    codigo: str
    cantidad: Decimal
    unitario: Decimal
    plan: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan", tuple(self.plan))

    @property
    def periodos_activos(self) -> int:
        """`n_p`: períodos con fracción mayor que cero."""
        return sum(1 for fraccion in self.plan if fraccion > CERO)

    @property
    def inicio(self) -> int:
        """`inicio_p`: el primer período con fracción mayor que cero (0 si no tiene)."""
        return next((n for n, fraccion in enumerate(self.plan, start=1) if fraccion > CERO), 0)


@dataclass(frozen=True, slots=True)
class PreciosDelCorte:
    """Los unitarios `u'` al corte por partida, con el método y la fuente que los produjo (S1):
    `comprobacion` (PU de la versión revalorada por UC-02) o `escalatoria` (S1 §8.3)."""

    metodo: str
    fuente: str
    unitarios: Mapping[str, Decimal]


@dataclass(frozen=True, slots=True)
class EstadoObra:
    """Todo lo que los cálculos puros necesitan al corte.

    `dia` es el número de día hábil del corte; `ejecutado` es `Q_p` (acumulado de las valuaciones
    registradas y no anuladas con *hasta* menor o igual al corte) y `por_periodo`, esa misma
    cantidad por (partida, período del *hasta*). `costo_real` es el AC de la perspectiva *costo*
    ya convertido a la moneda del proyecto (`None` si algún costo no tiene tasa aplicable, con su
    `motivo_costo`). `etiquetas` son las del plan base; `dia_ultima_valuacion` es el día hábil de
    la última valuación (0 si no hay).
    """

    partidas: tuple[PartidaControl, ...]
    etiquetas: tuple[str, ...]
    dias_por_periodo: int
    dia: int
    ejecutado: Mapping[str, Decimal]
    por_periodo: Mapping[tuple[str, int], Decimal]
    perspectiva: str = PERSPECTIVA_COSTO
    costo_real: Decimal | None = None
    motivo_costo: str = ""
    precios: PreciosDelCorte | None = None
    dia_ultima_valuacion: int = 0

    def __post_init__(self) -> None:
        if self.perspectiva not in (PERSPECTIVA_COSTO, PERSPECTIVA_PRECIO):
            raise ValueError(f"perspectiva {self.perspectiva!r}: se espera costo o precio")
        if self.dias_por_periodo < 1:
            raise ValueError("los dias por periodo deben ser 1 o mas")
        object.__setattr__(self, "partidas", tuple(self.partidas))
        object.__setattr__(self, "etiquetas", tuple(self.etiquetas))

    @property
    def periodos(self) -> int:
        """`N`: períodos del plan base."""
        return len(self.etiquetas)

    @property
    def dias_plan(self) -> int:
        """`D = N · L`: días hábiles del plan base."""
        return self.periodos * self.dias_por_periodo

    def cantidad_ejecutada(self, partida: PartidaControl) -> Decimal:
        """`qe_p = min(Q_p, q_p)` (S2-R8): la obra no presupuestada no gana valor."""
        return min(self.ejecutado.get(partida.codigo, CERO), partida.cantidad)

    def fraccion_planificada(self, partida: PartidaControl) -> Decimal:
        """`F_p(t)`: las fracciones de los períodos terminados más la parte proporcional, por días
        hábiles, del período que contiene al corte."""
        completos, transcurridos = divmod(self.dia, self.dias_por_periodo)
        hasta = min(completos, len(partida.plan))
        total = sum(partida.plan[:hasta], CERO)
        if transcurridos and completos < len(partida.plan):
            with _contexto():
                total += partida.plan[completos] * transcurridos / self.dias_por_periodo
        return min(total, UNO)


def partidas_de_plan(
    presupuesto: Presupuesto, plan: Sequence[PeriodoPlan], perspectiva: str
) -> tuple[PartidaControl, ...]:
    """Las partidas del presupuesto con su plan por período. Varios renglones del mismo código se
    suman (la cantidad) y comparten el unitario del primero, como `generar_curva`."""
    if perspectiva not in (PERSPECTIVA_COSTO, PERSPECTIVA_PRECIO):
        raise ValueError(f"perspectiva {perspectiva!r}: se espera costo o precio")
    cantidades: dict[str, Decimal] = defaultdict(lambda: CERO)
    unitarios: dict[str, Decimal] = {}
    for partida in presupuesto.partidas:
        codigo = partida.item.codigo_partida
        cantidades[codigo] += partida.item.cantidad
        unitarios.setdefault(
            codigo,
            partida.resultado.costo_directo
            if perspectiva == PERSPECTIVA_COSTO
            else partida.resultado.precio_unitario,
        )
    fracciones: dict[str, list[Decimal]] = {codigo: [CERO] * len(plan) for codigo in cantidades}
    for n, (_, reparto) in enumerate(plan):
        for codigo, fraccion in reparto:
            if codigo in fracciones:
                fracciones[codigo][n] += fraccion
    return tuple(
        PartidaControl(codigo, cantidades[codigo], unitarios[codigo], tuple(fracciones[codigo]))
        for codigo in cantidades
    )


def precios_por_escalatoria(
    unitarios: Mapping[str, Decimal],
    coeficientes: Mapping[str, Decimal],
    r: Decimal,
    fuente: str,
) -> PreciosDelCorte:
    """`u' = u · (1 + (K - 1)(1 - R))` por partida (S2 §4.3, S1 §8.3; INDICIO declarado en S1).
    `ValueError` si falta el coeficiente de alguna partida: no se supone `K = 1`."""
    faltan = sorted(set(unitarios) - set(coeficientes))
    if faltan:
        raise ValueError(f"falta el coeficiente K de las partidas {', '.join(faltan)}")
    if not CERO <= r < UNO:
        raise ValueError(f"R va en [0, 1): {r}")
    with _contexto():
        corte = {
            codigo: u * (UNO + (coeficientes[codigo] - UNO) * (UNO - r))
            for codigo, u in unitarios.items()
        }
    return PreciosDelCorte("escalatoria", fuente, corte)


# ---------------------------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Indicadores:
    """PV, EV, AC y sus índices al corte (§4.2). Un indicador que no se puede calcular es `None` y
    su motivo está en `no_disponible` (UC-20 1a-1d)."""

    bac: Decimal
    pv: Decimal
    ev: Decimal
    ac: Decimal | None
    sv: Decimal
    cv: Decimal | None
    spi: Decimal | None
    cpi: Decimal | None
    cpi_corte: Decimal | None
    eac_indice: Decimal | None
    eac_sistema: Decimal | None
    vac: Decimal | None
    termino_indice: int | None
    no_disponible: Mapping[str, str]


def _unitario_de_corte(estado: EstadoObra, codigo: str) -> Decimal | None:
    if estado.precios is None:
        return None
    return estado.precios.unitarios.get(codigo)


def _ac(estado: EstadoObra, motivos: dict[str, str]) -> Decimal | None:
    """AC de la perspectiva: el costo real declarado (*costo*) o `Σ qe·u'` (*precio*)."""
    if estado.perspectiva == PERSPECTIVA_COSTO:
        if estado.costo_real is None:
            motivos["AC"] = estado.motivo_costo or "sin costos reales declarados"
        return estado.costo_real
    total = CERO
    for partida in estado.partidas:
        qe = estado.cantidad_ejecutada(partida)
        if qe == CERO:
            continue
        precio = _unitario_de_corte(estado, partida.codigo)
        if precio is None:
            motivos["AC"] = f"sin precio del corte para la partida {partida.codigo}"
            return None
        total += qe * precio
    return total


def indicadores(estado: EstadoObra) -> Indicadores:
    """Los indicadores de valor ganado al corte (§4.2), en la moneda del proyecto."""
    motivos: dict[str, str] = {}
    with _contexto():
        bac = sum((p.cantidad * p.unitario for p in estado.partidas), CERO)
        pv = sum(
            (p.cantidad * p.unitario * estado.fraccion_planificada(p) for p in estado.partidas),
            CERO,
        )
        ev = sum(
            (estado.cantidad_ejecutada(p) * p.unitario for p in estado.partidas),
            CERO,
        )
        ac = _ac(estado, motivos)
        spi = ev / pv if pv > CERO else None
        if spi is None:
            motivos["SPI"] = "PV = 0: el corte es anterior a todo trabajo planificado"
        cpi = ev / ac if ac is not None and ac > CERO else None
        if ac == CERO:
            motivos["CPI"] = "AC = 0: aun no hay costos reales"
        cv = None if ac is None else ev - ac
        eac_indice = bac / cpi if cpi else None
        cpi_corte, eac_sistema = _eac_del_sistema(estado, ac, motivos)
        vac = None if eac_sistema is None else bac - eac_sistema
        termino = None
        if spi:
            termino = techo_de_dias(Decimal(estado.dias_plan) * pv / ev)
    for nombre in ("CV", "CPI", "EAC", "VAC"):
        if ac is None:
            motivos.setdefault(nombre, motivos.get("AC", "AC no disponible"))
    return Indicadores(
        bac=bac,
        pv=pv,
        ev=ev,
        ac=ac,
        sv=ev - pv,
        cv=cv,
        spi=spi,
        cpi=cpi,
        cpi_corte=cpi_corte,
        eac_indice=eac_indice,
        eac_sistema=eac_sistema,
        vac=vac,
        termino_indice=termino,
        no_disponible=dict(motivos),
    )


def _eac_del_sistema(
    estado: EstadoObra, ac: Decimal | None, motivos: dict[str, str]
) -> tuple[Decimal | None, Decimal | None]:
    """`CPIc = Σ qe·u' / AC` y `EAC = AC + Σ (q - qe)·u' / CPIc` (§4.2, propio de este trabajo)."""
    if ac is None or estado.precios is None:
        if ac is not None:
            motivos["EAC"] = "sin precios del corte"
        return None, None
    ejecutado_a_corte = CERO
    pendiente_a_corte = CERO
    for partida in estado.partidas:
        precio = _unitario_de_corte(estado, partida.codigo)
        if precio is None:
            motivos["EAC"] = f"sin precio del corte para la partida {partida.codigo}"
            return None, None
        qe = estado.cantidad_ejecutada(partida)
        ejecutado_a_corte += qe * precio
        pendiente_a_corte += (partida.cantidad - qe) * precio
    if ac == CERO or ejecutado_a_corte == CERO:
        motivos["EAC"] = "sin avance o sin costos reales: el rendimiento del consumo no existe"
        return None, None
    cpi_corte = ejecutado_a_corte / ac
    return cpi_corte, ac + pendiente_a_corte * ac / ejecutado_a_corte


# ---------------------------------------------------------------------------------------------
# Separación del desvío de control
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Separacion:
    """`CV = precio + consumo` (exacta) y, al término, `VAC = vac_precio + vac_consumo`.

    `plazo` es SV (cantidad y tiempo a precios de la línea base). Sin precios del corte, o sin AC,
    los componentes que dependen de ellos son `None` y `no_disponible` dice por qué (§4.3)."""

    plazo: Decimal
    precio: Decimal | None
    consumo: Decimal | None
    vac_precio: Decimal | None
    vac_consumo: Decimal | None
    metodo: str
    fuente: str
    no_disponible: Mapping[str, str]


def separar_desvio(estado: EstadoObra, calculados: Indicadores | None = None) -> Separacion:
    """Separa el desvío de control en plazo, precio y consumo (§4.3, S2-R1)."""
    ind = calculados or indicadores(estado)
    motivos: dict[str, str] = {}
    metodo = "" if estado.precios is None else estado.precios.metodo
    fuente = "" if estado.precios is None else estado.precios.fuente
    precio = consumo = vac_precio = vac_consumo = None
    sin_precio = sorted(
        p.codigo for p in estado.partidas if _unitario_de_corte(estado, p.codigo) is None
    )
    ejecutadas_sin_precio = [
        p.codigo
        for p in estado.partidas
        if p.codigo in sin_precio and estado.cantidad_ejecutada(p) > CERO
    ]
    with _contexto():
        if ejecutadas_sin_precio or estado.precios is None:
            motivos["precio"] = _motivo_sin_precios(estado, ejecutadas_sin_precio)
        else:
            precio = sum(
                (
                    estado.cantidad_ejecutada(p) * (p.unitario - estado.precios.unitarios[p.codigo])
                    for p in estado.partidas
                    if estado.cantidad_ejecutada(p) > CERO
                ),
                CERO,
            )
            if ind.ac is None:
                motivos["consumo"] = ind.no_disponible.get("AC", "AC no disponible")
            else:
                a_corte = sum(
                    (
                        estado.cantidad_ejecutada(p) * estado.precios.unitarios[p.codigo]
                        for p in estado.partidas
                        if estado.cantidad_ejecutada(p) > CERO
                    ),
                    CERO,
                )
                consumo = a_corte - ind.ac
        if sin_precio or estado.precios is None:
            motivos["vac_precio"] = _motivo_sin_precios(estado, sin_precio)
        else:
            vac_precio = -sum(
                (
                    p.cantidad * (estado.precios.unitarios[p.codigo] - p.unitario)
                    for p in estado.partidas
                ),
                CERO,
            )
            if ind.vac is not None:
                vac_consumo = ind.vac - vac_precio
            else:
                motivos["vac_consumo"] = ind.no_disponible.get("EAC", "EAC no disponible")
    return Separacion(ind.sv, precio, consumo, vac_precio, vac_consumo, metodo, fuente, motivos)


def _motivo_sin_precios(estado: EstadoObra, partidas: Sequence[str]) -> str:
    if estado.precios is None:
        return "sin precios del corte (S1): la separacion no esta disponible"
    return "sin precio del corte para " + ", ".join(partidas)


# ---------------------------------------------------------------------------------------------
# Reproyección al ritmo real
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProyeccionPartida:
    """Lo proyectado de una partida (§4.4). `fin` es el día hábil (con decimales) en que termina
    su obra pendiente; `None` si no le queda obra o no es proyectable (`motivo`)."""

    codigo: str
    indice: Decimal | None
    ritmo: Decimal | None
    pendiente: Decimal
    fin: Decimal | None
    detenida: bool = False
    sin_evidencia: bool = False
    motivo: str = ""


@dataclass(frozen=True, slots=True)
class Reproyeccion:
    """El plan reproyectado (lo ejecutado más lo proyectado, un `PeriodoPlan` válido para
    `generar_curva`), la proyección de cada partida y el término en días hábiles (`None` si alguna
    partida con obra pendiente no es proyectable)."""

    plan: tuple[PeriodoPlan, ...]
    partidas: tuple[ProyeccionPartida, ...]
    termino: int | None
    motivo_termino: str

    @property
    def detenidas(self) -> tuple[str, ...]:
        return tuple(p.codigo for p in self.partidas if p.detenida)

    @property
    def no_proyectables(self) -> tuple[str, ...]:
        return tuple(p.codigo for p in self.partidas if p.motivo)

    def de(self, codigo: str) -> ProyeccionPartida:
        return next(p for p in self.partidas if p.codigo == codigo)


def _etiqueta_siguiente(etiquetas: Sequence[str], numero: int) -> str:
    """La etiqueta del período `numero` si pasa del plan: «Semana 4» continúa «Semana 5»."""
    if etiquetas:
        encontrada = _ETIQUETA.match(etiquetas[-1])
        if encontrada:
            avance = numero - len(etiquetas)
            return f"{encontrada.group(1)}{int(encontrada.group(2)) + avance}"
    return f"Periodo {numero}"


def _ejecutado_por_periodo(
    estado: EstadoObra, partida: PartidaControl
) -> tuple[dict[int, Decimal], Decimal]:
    """Las fracciones ya ejecutadas de la partida por período (con tope en 1, S2-R8) y su suma."""
    fracciones: dict[int, Decimal] = {}
    acumulado = CERO
    periodos = sorted(n for (codigo, n) in estado.por_periodo if codigo == partida.codigo)
    with _contexto():
        for n in periodos:
            fraccion = min(
                estado.por_periodo[(partida.codigo, n)] / partida.cantidad, UNO - acumulado
            )
            if fraccion > CERO:
                fracciones[n] = fracciones.get(n, CERO) + fraccion
                acumulado += fraccion
    if estado.cantidad_ejecutada(partida) == partida.cantidad and fracciones:
        ultimo = max(fracciones)
        fracciones[ultimo] += UNO - acumulado
        acumulado = UNO
    return fracciones, acumulado


def reproyectar(
    estado: EstadoObra,
    *,
    multiplicador: Mapping[str, Decimal] | None = None,
    adelantar: Collection[str] = (),
) -> Reproyeccion:
    """Reproyecta el plan al ritmo real (§4.4).

    `multiplicador` escala el ritmo de una partida (más cuadrillas, horas extra) y `adelantar`
    lleva su inicio al período siguiente al corte (partidas en paralelo). Cada partida con obra
    pendiente avanza a `r = s / n · multiplicador` por período, con `s` el índice de la partida
    (`EV_p / PV_p`) o, sin evidencia propia, el SPI global."""
    multiplicador = multiplicador or {}
    cantidad_de_periodos = estado.periodos
    siguiente, restantes = _corte(estado)
    ind = indicadores(estado)
    ritmos: dict[str, tuple[dict[int, Decimal], ProyeccionPartida]] = {}
    for partida in estado.partidas:
        ritmos[partida.codigo] = _proyectar_partida(
            estado,
            partida,
            ind.spi,
            multiplicador.get(partida.codigo, UNO),
            partida.codigo in adelantar,
            (siguiente, restantes),
        )
    ultimo = max(
        [cantidad_de_periodos] + [max(fracciones, default=0) for fracciones, _ in ritmos.values()]
    )
    plan: list[PeriodoPlan] = []
    for n in range(1, ultimo + 1):
        etiqueta = (
            estado.etiquetas[n - 1]
            if n <= cantidad_de_periodos
            else _etiqueta_siguiente(estado.etiquetas, n)
        )
        reparto = tuple(
            (partida.codigo, ritmos[partida.codigo][0][n])
            for partida in estado.partidas
            if ritmos[partida.codigo][0].get(n, CERO) > CERO
        )
        plan.append((etiqueta, reparto))
    while len(plan) > 1 and not plan[-1][1]:
        plan.pop()
    proyecciones = tuple(proyeccion for _, proyeccion in ritmos.values())
    termino, motivo = _termino(estado, proyecciones)
    return Reproyeccion(tuple(plan), proyecciones, termino, motivo)


def proyectar_partida(
    estado: EstadoObra,
    codigo: str,
    *,
    multiplicador: Decimal = UNO,
    adelantada: bool = False,
    spi_global: Decimal | None = None,
) -> ProyeccionPartida:
    """La proyección de una sola partida: lo mismo que `reproyectar` hace con cada una, sin
    recorrer las demás. `spi_global` es el de `indicadores(estado).spi`."""
    partida = next(p for p in estado.partidas if p.codigo == codigo)
    siguiente, restantes = _corte(estado)
    return _proyectar_partida(
        estado, partida, spi_global, multiplicador, adelantada, (siguiente, restantes)
    )[1]


def fin_excede(fin: Decimal, objetivo: int) -> bool:
    """True si el día hábil `fin` (con decimales) pasa del día `objetivo`: la igualdad exacta
    cuenta como recuperado (§7.3)."""
    return fin.quantize(PRECISION_DE_DIAS) > objetivo


def _corte(estado: EstadoObra) -> tuple[int, int]:
    """El período siguiente al corte y los días hábiles que le quedan."""
    completos, transcurridos = divmod(estado.dia, estado.dias_por_periodo)
    return completos + 1, estado.dias_por_periodo - transcurridos


def _proyectar_partida(
    estado: EstadoObra,
    partida: PartidaControl,
    spi_global: Decimal | None,
    multiplicador: Decimal,
    adelantada: bool,
    corte: tuple[int, int],
) -> tuple[dict[int, Decimal], ProyeccionPartida]:
    siguiente, restantes = corte
    largo = estado.dias_por_periodo
    if partida.cantidad == CERO:
        base = {n: f for n, f in enumerate(partida.plan, start=1) if f > CERO}
        return base, ProyeccionPartida(partida.codigo, None, None, CERO, None)
    hechas, hecho = _ejecutado_por_periodo(estado, partida)
    pendiente = UNO - hecho
    fracciones = dict(hechas)
    if pendiente <= CERO:
        return fracciones, ProyeccionPartida(partida.codigo, None, None, CERO, None)
    qe = estado.cantidad_ejecutada(partida)
    planificada = estado.fraccion_planificada(partida)
    detenida = planificada > CERO and qe == CERO
    with _contexto():
        if planificada > CERO and qe > CERO:
            indice: Decimal | None = qe / (partida.cantidad * planificada)
            sin_evidencia = False
        else:
            indice = UNO if spi_global is None else spi_global
            sin_evidencia = not detenida
    if partida.periodos_activos == 0:
        return fracciones, ProyeccionPartida(
            partida.codigo, indice, None, pendiente, None, motivo="la partida no esta en el plan"
        )
    if not indice:
        return fracciones, ProyeccionPartida(
            partida.codigo,
            indice,
            None,
            pendiente,
            None,
            detenida=detenida,
            motivo="el SPI global es 0: sin ritmo no se proyecta",
        )
    with _contexto():
        ritmo = indice / partida.periodos_activos * multiplicador
    empezada = qe > CERO or partida.inicio <= siguiente
    inicio = siguiente if (empezada or adelantada) else partida.inicio
    restante = pendiente
    n = inicio
    ultimo_n, ultima = inicio, CERO
    while restante > CERO:
        if n - inicio > LIMITE_DE_PERIODOS:
            raise ValueError("la reproyeccion no termina: el ritmo es demasiado bajo")
        with _contexto():
            tope = ritmo * restantes / largo if n == siguiente else ritmo
        tomado = min(tope, restante)
        fracciones[n] = fracciones.get(n, CERO) + tomado
        restante -= tomado
        ultimo_n, ultima = n, tomado
        n += 1
    with _contexto():
        base = estado.dia if ultimo_n == siguiente else (ultimo_n - 1) * largo
        fin = Decimal(base) + ultima * largo / ritmo
    return fracciones, ProyeccionPartida(
        partida.codigo,
        indice,
        ritmo,
        pendiente,
        fin,
        detenida=detenida,
        sin_evidencia=sin_evidencia,
    )


def _termino(
    estado: EstadoObra, proyecciones: Sequence[ProyeccionPartida]
) -> tuple[int | None, str]:
    sin_ritmo = [p.codigo for p in proyecciones if p.motivo]
    if sin_ritmo:
        return None, "no proyectable: " + ", ".join(sin_ritmo)
    fines = [p.fin for p in proyecciones if p.fin is not None]
    if not fines:
        return estado.dia_ultima_valuacion, "nada queda pendiente: la fecha de la ultima valuacion"
    return techo_de_dias(max(fines)), ""


# ---------------------------------------------------------------------------------------------
# Punto de equilibrio proyectado y alertas
# ---------------------------------------------------------------------------------------------


def equilibrio_proyectado(
    *,
    venta: Decimal,
    costo_variable: Decimal,
    costo_fijo: Decimal,
    dias_plan: int,
    dias_proyectados: int,
    reajuste_reconocido: Decimal,
    curva: Sequence[PuntoCurva],
) -> PuntoEquilibrio:
    """El punto de equilibrio con `V' = V + reajuste reconocido`, `CV'` dado y `CF' = CF · D'/D`
    (S2-R7), ubicado en la curva reproyectada (§4.7). No suma ningún reajuste proyectado: recibe
    el ya reconocido como dato (S2-R15). `curva` es la del plan reproyectado sobre la venta `V`:
    se reescala a `V'` para ubicar el punto por su fracción del total."""
    if dias_plan < 1:
        raise ValueError("los dias del plan base deben ser 1 o mas")
    with _contexto():
        venta_proyectada = venta + reajuste_reconocido
        fijo = costo_fijo * dias_proyectados / dias_plan
        if reajuste_reconocido != CERO and venta != CERO:
            curva = tuple(
                PuntoCurva(
                    p.periodo,
                    p.monto * venta_proyectada / venta,
                    p.acumulado * venta_proyectada / venta,
                )
                for p in curva
            )
        return equilibrio(venta_proyectada, costo_variable, fijo, curva)


@dataclass(frozen=True, slots=True)
class Alerta:
    """Una alerta con su umbral y la naturaleza de este (§4.5)."""

    codigo: str
    severidad: Severidad
    descripcion: str
    valor_observado: Decimal | None
    umbral: Decimal | None
    naturaleza_umbral: str = NATURALEZA_DECLARADA


@dataclass(frozen=True, slots=True)
class Alertas:
    """Las alertas que saltaron y las que no se pudieron evaluar, con el motivo (UC-20 1a-1d)."""

    alertas: tuple[Alerta, ...]
    no_evaluadas: Mapping[str, str]


def alertas(
    ind: Indicadores,
    sep: Separacion,
    reproyeccion: Reproyeccion,
    *,
    dias_plan: int,
    equilibrio_base: PuntoEquilibrio | None,
    equilibrio_proyectado: PuntoEquilibrio | None,
    parametros: ParametrosControl,
) -> Alertas:
    """Evalúa AL-1 a AL-6 (§4.5). Si el indicador de una alerta no está disponible, no se evalúa."""
    salidas: list[Alerta] = []
    no_evaluadas: dict[str, str] = {}
    if ind.spi is None:
        no_evaluadas["AL-1"] = ind.no_disponible.get("SPI", "SPI no aplica")
    elif ind.spi < UNO:
        error = ind.spi < parametros.spi_error
        salidas.append(
            Alerta(
                "AL-1",
                Severidad.ERROR if error else Severidad.ADVERTENCIA,
                f"retraso: SPI {_cuatro(ind.spi)}",
                ind.spi,
                parametros.spi_error,
            )
        )
    if ind.cpi is None:
        no_evaluadas["AL-2"] = ind.no_disponible.get("CPI", "CPI no disponible")
    elif ind.cpi < UNO:
        error = ind.cpi < parametros.cpi_error
        salidas.append(
            Alerta(
                "AL-2",
                Severidad.ERROR if error else Severidad.ADVERTENCIA,
                f"sobrecosto: CPI {_cuatro(ind.cpi)}",
                ind.cpi,
                parametros.cpi_error,
            )
        )
    salidas.extend(_alerta_de_termino(reproyeccion, dias_plan, parametros, no_evaluadas))
    salidas.extend(
        _alerta_de_equilibrio(equilibrio_base, equilibrio_proyectado, parametros, no_evaluadas)
    )
    if sep.precio is None or ind.ev <= CERO:
        no_evaluadas["AL-5"] = sep.no_disponible.get("precio", "sin avance ejecutado")
    elif abs(sep.precio) >= parametros.precio_info * ind.ev:
        salidas.append(
            Alerta(
                "AL-5",
                Severidad.INFO,
                "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvia "
                f"{sep.precio} sobre un valor ganado de {ind.ev}",
                abs(sep.precio),
                parametros.precio_info * ind.ev,
            )
        )
    salidas.extend(
        Alerta(
            "AL-6",
            Severidad.ADVERTENCIA,
            f"la partida {codigo} tiene trabajo planificado y ningun avance (detenida)",
            None,
            None,
        )
        for codigo in reproyeccion.detenidas
    )
    return Alertas(tuple(salidas), no_evaluadas)


def _cuatro(valor: Decimal) -> str:
    return format(valor.quantize(Decimal("0.0001")), "f")


def _alerta_de_termino(
    reproyeccion: Reproyeccion,
    dias_plan: int,
    parametros: ParametrosControl,
    no_evaluadas: dict[str, str],
) -> list[Alerta]:
    if reproyeccion.termino is None:
        no_evaluadas["AL-3"] = reproyeccion.motivo_termino
        return []
    retraso = reproyeccion.termino - dias_plan
    if retraso <= 0:
        return []
    error = Decimal(retraso) > parametros.retraso_error * dias_plan
    return [
        Alerta(
            "AL-3",
            Severidad.ERROR if error else Severidad.ADVERTENCIA,
            f"el termino proyectado (dia {reproyeccion.termino}) pasa {retraso} dia(s) habil(es) "
            f"del plan base (dia {dias_plan})",
            Decimal(retraso),
            parametros.retraso_error * dias_plan,
        )
    ]


def _alerta_de_equilibrio(
    base: PuntoEquilibrio | None,
    proyectado: PuntoEquilibrio | None,
    parametros: ParametrosControl,
    no_evaluadas: dict[str, str],
) -> list[Alerta]:
    if proyectado is None or base is None:
        no_evaluadas["AL-4"] = "el punto de equilibrio no aplica o AC no esta disponible"
        return []
    if proyectado.estado in (EstadoEquilibrio.NO_SE_ALCANZA, EstadoEquilibrio.NO_EXISTE):
        return [
            Alerta(
                "AL-4",
                Severidad.ERROR,
                f"el punto de equilibrio proyectado: {proyectado.mensaje}",
                proyectado.porcentaje,
                base.porcentaje,
            )
        ]
    if (
        proyectado.porcentaje is not None
        and base.porcentaje is not None
        and proyectado.porcentaje - base.porcentaje > parametros.equilibrio_puntos
    ):
        return [
            Alerta(
                "AL-4",
                Severidad.ADVERTENCIA,
                "el punto de equilibrio proyectado sube mas de "
                f"{parametros.equilibrio_puntos} puntos porcentuales sobre el de la linea base",
                proyectado.porcentaje - base.porcentaje,
                parametros.equilibrio_puntos,
            )
        ]
    return []
