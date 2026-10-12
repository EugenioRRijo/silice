# core/budget/recuperacion.py
"""SL-E6: opciones de recuperación de un retraso (spec S2 §4.6). Funciones **puras**, sin base de
datos ni `sqlalchemy`; la decisión que crea la versión vive en `core.budget.decision`.

Cuatro opciones, cada una calculada sola (sin combinar) desde el rendimiento y la cuadrilla del APU
de cada partida y un factor de eficiencia declarado por rendimientos decrecientes (horizonte §4;
Lee, 2022 es la base del método, **no** de las cifras):

* **más cuadrillas**: con `k` cuadrillas iguales a la del APU el ritmo se multiplica por
  `E(k) = Σ η^(j-1)`, `η = 0,80`, `k` hasta `cuadrillas_max = 3`;
* **horas extra**: `h` horas por día dentro de los límites verificados de la LOTTT (arts. 118, 173,
  178 y 182), con ritmo `1 + (h/8)·η_he`;
* **partidas en paralelo**: partidas sin empezar se adelantan al período siguiente al corte; exige
  la declaración del usuario de que no dependen de las que están en curso (S2-R4);
* **aceptar el retraso**: el plan reproyectado, con su costo indirecto y la penalización del
  contrato.

Una partida sin mano de obra a jornal (solo destajo o sin mano de obra) no tiene cuadrilla que
escalar: «más cuadrillas» y «horas extra» devuelven «no aplica» para ella **antes** de dividir. Los
supuestos de cada resultado se listan con su naturaleza.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from core.budget.curva import PeriodoPlan, generar_curva
from core.budget.equilibrio import PuntoEquilibrio
from core.budget.valor_ganado import (
    CERO,
    PERSPECTIVA_COSTO,
    UNO,
    EstadoObra,
    Indicadores,
    ParametrosControl,
    Reproyeccion,
    equilibrio_proyectado,
    fin_excede,
    proyectar_partida,
    reproyectar,
    techo_de_dias,
)
from core.contracts.apu import ComposicionAPU, ModalidadManoObra, ParametrosCosto
from core.contracts.presupuesto import Presupuesto

__all__ = [
    "HORAS_EXTRA_ANIO_MAX",
    "HORAS_EXTRA_DIA_MAX",
    "HORAS_EXTRA_SEMANA_MAX",
    "HORAS_JORNADA",
    "OPCIONES",
    "ContextoRecuperacion",
    "CostoDiario",
    "LimiteLegal",
    "Opcion",
    "Supuesto",
    "costo_diario",
    "eficiencia_de_cuadrillas",
    "exigir_horas_extra_legales",
    "opcion_aceptar",
    "opcion_cuadrillas",
    "opcion_horas_extra",
    "opcion_paralelo",
    "opciones",
]

OPCIONES = ("cuadrillas", "horas_extra", "paralelo", "aceptar")
TITULOS = {
    "cuadrillas": "Mas cuadrillas",
    "horas_extra": "Horas extra",
    "paralelo": "Partidas en paralelo",
    "aceptar": "Aceptar el retraso",
}
#: Límites de la LOTTT (G.O. 6.076 Ext., 07-05-2012), verificados en la copia del repositorio.
HORAS_JORNADA = Decimal(8)  # art. 173: jornada diurna
HORAS_EXTRA_DIA_MAX = Decimal(2)  # art. 178: duración efectiva con extras <= 10 h diarias
HORAS_EXTRA_SEMANA_MAX = Decimal(10)  # art. 178
HORAS_EXTRA_ANIO_MAX = Decimal(100)  # art. 178
DIAS_POR_SEMANA = 5  # art. 173: cinco días a la semana
FUENTE_LOTTT = "LOTTT G.O. 6.076 Ext. 07-05-2012 (docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt)"
NATURALEZA_FUENTE = "FUENTE_VERIFICADA"
NATURALEZA_DATO = "DATO_DEL_CONTRATO"
NATURALEZA_SUPUESTO = "SUPUESTO_DECLARADO"
PERMISO_ART_182 = "permiso de la Inspectoria del Trabajo (LOTTT art. 182) para las horas extra"


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


class LimiteLegal(ValueError):  # noqa: N818
    """Una opción de horas extra que supera un límite de la LOTTT."""


@dataclass(frozen=True, slots=True)
class Supuesto:
    """Un dato con que se calculó una opción, con su naturaleza (fuente o supuesto declarado)."""

    nombre: str
    valor: str
    naturaleza: str
    fuente: str = ""


@dataclass(frozen=True, slots=True)
class CostoDiario:
    """El componente dependiente del tiempo del APU (§4.6): `costo_dia = C_d` (cuadrilla a jornal
    con FCAS y bono, más equipos), `salario = S` (jornales sin FCAS) y `rendimiento = R`. Si la
    partida no tiene mano de obra a jornal o no tiene rendimiento, `motivo` dice por qué «no
    aplica»."""

    codigo: str
    costo_dia: Decimal
    salario: Decimal
    rendimiento: Decimal
    motivo: str = ""

    @property
    def aplica(self) -> bool:
        return not self.motivo


def costo_diario(composicion: ComposicionAPU, parametros: ParametrosCosto) -> CostoDiario:
    """`C_d = Σ_jornal cantidad·sueldo·(1 + FCAS) + bono·obreros_a_jornal + Σ cantidad·precio·dep`;
    `S = Σ_jornal cantidad·sueldo`. Las líneas a destajo se pagan por unidad y los materiales no
    dependen del tiempo: ninguna opción los cambia."""
    jornal = [m for m in composicion.mano_obra if m.modalidad is ModalidadManoObra.JORNAL]
    salario = sum((m.cantidad * m.sueldo for m in jornal), CERO)
    equipos = sum((e.cantidad * e.precio * e.depreciacion for e in composicion.equipos), CERO)
    costo_dia = (
        salario * (UNO + parametros.fcas) + parametros.bono_alimentacion * composicion.total_obreros
    ) + equipos
    motivo = ""
    if composicion.rendimiento <= CERO:
        motivo = "sin rendimiento"
    elif salario == CERO:
        motivo = "sin mano de obra a jornal"
    return CostoDiario(
        composicion.codigo_partida, costo_dia, salario, composicion.rendimiento, motivo
    )


def eficiencia_de_cuadrillas(cuadrillas: int, eta: Decimal) -> Decimal:
    """`E(k) = Σ_{j=1..k} η^(j-1)`: lo que rinden `k` cuadrillas respecto de una (§4.6.1)."""
    with _contexto():
        return sum((eta ** (j - 1) for j in range(1, cuadrillas + 1)), CERO)


def exigir_horas_extra_legales(
    horas_por_dia: Decimal, dias_con_extra: int, previas: Decimal
) -> None:
    """`LimiteLegal` si `h` horas extra por día durante `dias_con_extra` días llevan a un obrero
    más allá de 2 h por día (10 h de duración efectiva, art. 178), 10 h extra por semana o 100 h
    extra por año (con las `previas` del año). El límite exacto pasa."""
    if horas_por_dia < CERO:
        raise LimiteLegal(f"las horas extra por dia no pueden ser negativas: {horas_por_dia}")
    if horas_por_dia > HORAS_EXTRA_DIA_MAX:
        raise LimiteLegal(
            f"{horas_por_dia} h extra por dia superan las {HORAS_EXTRA_DIA_MAX} h que dejan la "
            f"duracion efectiva en 10 h (LOTTT art. 178; {FUENTE_LOTTT})"
        )
    if horas_por_dia * DIAS_POR_SEMANA > HORAS_EXTRA_SEMANA_MAX:
        raise LimiteLegal(
            f"{horas_por_dia} h extra por dia son {horas_por_dia * DIAS_POR_SEMANA} h por semana, "
            f"mas de las {HORAS_EXTRA_SEMANA_MAX} h del art. 178"
        )
    anuales = previas + horas_por_dia * dias_con_extra
    if anuales > HORAS_EXTRA_ANIO_MAX:
        raise LimiteLegal(
            f"un obrero llegaria a {anuales} h extra en el año, mas de las "
            f"{HORAS_EXTRA_ANIO_MAX} h del art. 178"
        )


@dataclass(frozen=True)
class ContextoRecuperacion:
    """Todo lo que las opciones necesitan: el estado al corte, la reproyección base, los
    indicadores, los APU de la línea base (o los revalorados, `origen_costo_diario`), los
    parámetros y los montos del punto de equilibrio. `objetivo` es el término objetivo en días
    hábiles (por defecto el fin del plan base). `horas_previas` son las horas extra que el obrero
    ya acumula en el año (dato declarado, por defecto 0)."""

    estado: EstadoObra
    base: Reproyeccion
    indicadores: Indicadores
    composiciones: Mapping[str, ComposicionAPU]
    parametros_costo: ParametrosCosto
    parametros: ParametrosControl
    presupuesto: Presupuesto
    venta: Decimal
    costo_fijo: Decimal
    reajuste: Decimal = CERO
    objetivo: int | None = None
    origen_costo_diario: str = "composiciones de la linea base"
    horas_previas: Decimal = CERO
    independientes: frozenset[str] = field(default_factory=frozenset)

    @property
    def meta(self) -> int:
        return self.estado.dias_plan if self.objetivo is None else self.objetivo


@dataclass(frozen=True)
class Opcion:
    """El resultado de una opción (§4.6). `eac` es el costo directo final proyectado de la opción
    (`CV'` del punto de equilibrio); `costo_indirecto = CF' - CF`; `retraso` son los días hábiles
    que quedan sobre el objetivo; `detalle` es serializable a JSON (textos y números)."""

    nombre: str
    aplica: bool
    motivo: str
    plan: tuple[PeriodoPlan, ...] = ()
    termino: int | None = None
    retraso: int | None = None
    costo_directo_adicional: Decimal = CERO
    costo_indirecto: Decimal = CERO
    penalizacion: Decimal = CERO
    eac: Decimal | None = None
    equilibrio: PuntoEquilibrio | None = None
    detalle: Mapping[str, object] = field(default_factory=dict)
    supuestos: tuple[Supuesto, ...] = ()
    requisitos: tuple[str, ...] = ()
    requiere_declaracion: bool = False

    @property
    def titulo(self) -> str:
        return TITULOS[self.nombre]


def _no_aplica(nombre: str, motivo: str, supuestos: tuple[Supuesto, ...] = ()) -> Opcion:
    return Opcion(nombre, False, motivo, supuestos=supuestos)


def _supuestos_comunes(contexto: ContextoRecuperacion) -> tuple[Supuesto, ...]:
    parametros = contexto.parametros
    return (
        Supuesto(
            "penalizacion diaria",
            str(parametros.penalizacion_diaria),
            NATURALEZA_DATO,
            parametros.fuente_penalizacion or "sin fuente: ninguna norma verificada la fija",
        ),
        Supuesto("costo diario de la cuadrilla", contexto.origen_costo_diario, NATURALEZA_SUPUESTO),
        Supuesto("costo fijo en el tiempo", "CF' = CF · D'/D", NATURALEZA_SUPUESTO),
    )


def _cerrar(
    contexto: ContextoRecuperacion,
    nombre: str,
    reproyeccion: Reproyeccion,
    adicional: Decimal,
    supuestos: tuple[Supuesto, ...],
    detalle: Mapping[str, object],
    *,
    requisitos: tuple[str, ...] = (),
    requiere_declaracion: bool = False,
) -> Opcion:
    """Completa una opción con su término, sus costos indirectos y su punto de equilibrio."""
    termino = reproyeccion.termino
    if termino is None:
        return _no_aplica(nombre, reproyeccion.motivo_termino, supuestos)
    retraso = max(0, termino - contexto.meta)
    with _contexto():
        fijo = contexto.costo_fijo * termino / contexto.estado.dias_plan
        indirecto = fijo - contexto.costo_fijo
        penalizacion = contexto.parametros.penalizacion_diaria * retraso
    eac = None
    punto = None
    if contexto.indicadores.eac_sistema is not None:
        eac = contexto.indicadores.eac_sistema + adicional
        if contexto.estado.perspectiva == PERSPECTIVA_COSTO:
            punto = equilibrio_proyectado(
                venta=contexto.venta,
                costo_variable=eac,
                costo_fijo=contexto.costo_fijo,
                dias_plan=contexto.estado.dias_plan,
                dias_proyectados=termino,
                reajuste_reconocido=contexto.reajuste,
                curva=generar_curva(contexto.presupuesto, reproyeccion.plan),
            )
    return Opcion(
        nombre,
        True,
        "",
        reproyeccion.plan,
        termino,
        retraso,
        adicional,
        indirecto,
        penalizacion,
        eac,
        punto,
        detalle,
        (*supuestos, *_supuestos_comunes(contexto)),
        requisitos,
        requiere_declaracion,
    )


def _determinantes(contexto: ContextoRecuperacion) -> list[str]:
    """Las partidas que determinan el término: las de `fin > objetivo` en la reproyección base."""
    return [
        p.codigo
        for p in contexto.base.partidas
        if p.fin is not None and fin_excede(p.fin, contexto.meta)
    ]


def _cantidad_restante(contexto: ContextoRecuperacion, codigo: str) -> Decimal:
    partida = next(p for p in contexto.estado.partidas if p.codigo == codigo)
    return partida.cantidad - contexto.estado.cantidad_ejecutada(partida)


def _costos_diarios(
    contexto: ContextoRecuperacion, codigos: list[str]
) -> tuple[dict[str, CostoDiario], dict[str, str]]:
    aplican: dict[str, CostoDiario] = {}
    no_aplican: dict[str, str] = {}
    for codigo in codigos:
        composicion = contexto.composiciones.get(codigo)
        if composicion is None:
            no_aplican[codigo] = "sin composicion de APU"
            continue
        costo = costo_diario(composicion, contexto.parametros_costo)
        if costo.aplica:
            aplican[codigo] = costo
        else:
            no_aplican[codigo] = costo.motivo
    return aplican, no_aplican


# ---------------------------------------------------------------------------------------------
# Más cuadrillas
# ---------------------------------------------------------------------------------------------


def opcion_cuadrillas(contexto: ContextoRecuperacion) -> Opcion:
    """Más cuadrillas (§4.6.1). Para cada partida que determina el término, el menor `k` en
    `2 .. cuadrillas_max` con `fin <= objetivo` (o `cuadrillas_max` si ninguno alcanza); costo
    adicional `ΔCD = q_rest · C_d · (k - E(k)) / (R · E(k))`."""
    parametros = contexto.parametros
    supuestos = (
        Supuesto(
            "eta de cuadrillas",
            str(parametros.eta_cuadrilla),
            NATURALEZA_SUPUESTO,
            "Lee (2022) es la base del metodo, no del valor",
        ),
        Supuesto("cuadrillas maximas", str(parametros.cuadrillas_max), NATURALEZA_SUPUESTO),
    )
    determinantes = _determinantes(contexto)
    if not determinantes:
        return _no_aplica("cuadrillas", "ninguna partida pasa del objetivo", supuestos)
    aplican, no_aplican = _costos_diarios(contexto, determinantes)
    if not aplican:
        motivos = "; ".join(f"{c}: {m}" for c, m in no_aplican.items())
        return _no_aplica("cuadrillas", f"no aplica ({motivos})", supuestos)
    multiplicadores: dict[str, Decimal] = {}
    elegidas: dict[str, object] = {}
    adicional = CERO
    for codigo, costo in aplican.items():
        elegido = parametros.cuadrillas_max
        for k in range(2, parametros.cuadrillas_max + 1):
            eficiencia = eficiencia_de_cuadrillas(k, parametros.eta_cuadrilla)
            fin = proyectar_partida(
                contexto.estado,
                codigo,
                multiplicador=eficiencia,
                spi_global=contexto.indicadores.spi,
            ).fin
            if fin is not None and not fin_excede(fin, contexto.meta):
                elegido = k
                break
        eficiencia = eficiencia_de_cuadrillas(elegido, parametros.eta_cuadrilla)
        multiplicadores[codigo] = eficiencia
        with _contexto():
            delta = (
                _cantidad_restante(contexto, codigo)
                * costo.costo_dia
                * (elegido - eficiencia)
                / (costo.rendimiento * eficiencia)
            )
        adicional += delta
        elegidas[codigo] = {"k": elegido, "eficiencia": str(eficiencia), "adicional": str(delta)}
    reproyeccion = reproyectar(contexto.estado, multiplicador=multiplicadores)
    return _cerrar(
        contexto,
        "cuadrillas",
        reproyeccion,
        adicional,
        supuestos,
        {"partidas": elegidas, "sin_cuadrilla": no_aplican},
    )


# ---------------------------------------------------------------------------------------------
# Horas extra
# ---------------------------------------------------------------------------------------------


def opcion_horas_extra(contexto: ContextoRecuperacion) -> Opcion:
    """Horas extra (§4.6.2): `h = horas_extra_dia` en cada partida que determina el término, con
    ritmo `r · (1 + (h/8)·η_he)` y costo de un día de cuadrilla `C_d + OT`,
    `OT = (h/8)(1 + recargo)·S·(1 + FCAS·a)`; `ΔCD = q_rest · (C_d + OT - C_d·m) / (R·m)`, con
    `m = 1 + h·η_he/8`. `ValueError` (`LimiteLegal`) si `h` supera los límites diarios o semanales;
    la opción no aplica si un obrero pasaría de 100 h extra en el año."""
    parametros = contexto.parametros
    horas = parametros.horas_extra_dia
    exigir_horas_extra_legales(horas, 0, CERO)
    supuestos = (
        Supuesto("horas extra por dia", str(horas), NATURALEZA_SUPUESTO, "tope legal 2 h"),
        Supuesto("eta de horas extra", str(parametros.eta_horas_extra), NATURALEZA_SUPUESTO),
        Supuesto(
            "recargo",
            str(parametros.recargo_horas_extra),
            NATURALEZA_FUENTE,
            "LOTTT art. 118: por lo menos 50 %",
        ),
        Supuesto(
            "FCAS sobre las horas extra",
            "si" if parametros.fcas_en_horas_extra else "no",
            NATURALEZA_SUPUESTO,
            "interpretacion de los arts. 104 y 178; decide el tutor",
        ),
        Supuesto("jornada ordinaria", f"{HORAS_JORNADA} h", NATURALEZA_FUENTE, "LOTTT art. 173"),
        Supuesto(
            "limites de horas extra",
            "10 h por semana, 100 h por año",
            NATURALEZA_FUENTE,
            "LOTTT art. 178",
        ),
    )
    determinantes = _determinantes(contexto)
    if not determinantes:
        return _no_aplica("horas_extra", "ninguna partida pasa del objetivo", supuestos)
    aplican, no_aplican = _costos_diarios(contexto, determinantes)
    if not aplican:
        motivos = "; ".join(f"{c}: {m}" for c, m in no_aplican.items())
        return _no_aplica("horas_extra", f"no aplica ({motivos})", supuestos)
    with _contexto():
        multiplicador = UNO + horas * parametros.eta_horas_extra / HORAS_JORNADA
        incluye_fcas = parametros.fcas_en_horas_extra
        factor_fcas = UNO + (contexto.parametros_costo.fcas if incluye_fcas else CERO)
    reproyeccion = reproyectar(contexto.estado, multiplicador=dict.fromkeys(aplican, multiplicador))
    adicional = CERO
    por_partida: dict[str, object] = {}
    peor = 0
    for codigo, costo in aplican.items():
        with _contexto():
            extra = (
                horas
                / HORAS_JORNADA
                * (UNO + parametros.recargo_horas_extra)
                * costo.salario
                * factor_fcas
            )
            delta = (
                _cantidad_restante(contexto, codigo)
                * (costo.costo_dia + extra - costo.costo_dia * multiplicador)
                / (costo.rendimiento * multiplicador)
            )
        fin = reproyeccion.de(codigo).fin
        dias = max(0, techo_de_dias(fin) - contexto.estado.dia) if fin is not None else 0
        peor = max(peor, dias)
        adicional += delta
        por_partida[codigo] = {
            "dias": dias,
            "horas_extra_del_obrero": str(horas * dias),
            "adicional": str(delta),
        }
    try:
        exigir_horas_extra_legales(horas, peor, contexto.horas_previas)
    except LimiteLegal as error:
        return _no_aplica("horas_extra", str(error), supuestos)
    return _cerrar(
        contexto,
        "horas_extra",
        reproyeccion,
        adicional,
        supuestos,
        {"partidas": por_partida, "sin_cuadrilla": no_aplican, "horas_por_dia": str(horas)},
        requisitos=(PERMISO_ART_182,),
    )


# ---------------------------------------------------------------------------------------------
# Partidas en paralelo y aceptar el retraso
# ---------------------------------------------------------------------------------------------


def opcion_paralelo(contexto: ContextoRecuperacion) -> Opcion:
    """Partidas en paralelo (§4.6.3): las partidas sin empezar con `inicio > c + 1` se adelantan al
    período siguiente al corte. Costo directo adicional 0 según el APU. Exige la declaración del
    usuario de que no dependen de las que están en curso (`requiere_declaracion`)."""
    estado = contexto.estado
    siguiente = estado.dia // estado.dias_por_periodo + 1
    candidatas = [
        p.codigo
        for p in estado.partidas
        if estado.cantidad_ejecutada(p) == CERO
        and estado.fraccion_planificada(p) == CERO
        and p.inicio > siguiente
    ]
    if not candidatas:
        return _no_aplica(
            "paralelo", "ninguna partida sin empezar con inicio posterior al periodo siguiente"
        )
    reproyeccion = reproyectar(estado, adelantar=candidatas)
    simultaneas = max(
        (len(reparto) for _, reparto in reproyeccion.plan),
        default=0,
    )
    return _cerrar(
        contexto,
        "paralelo",
        reproyeccion,
        CERO,
        (
            Supuesto(
                "independencia de las partidas",
                ", ".join(candidatas),
                NATURALEZA_SUPUESTO,
                "el plan no tiene dependencias: el usuario lo declara con su fuente (S2-R4)",
            ),
        ),
        {"adelantadas": candidatas, "partidas_simultaneas_maximas": simultaneas},
        requiere_declaracion=True,
    )


def opcion_aceptar(contexto: ContextoRecuperacion) -> Opcion:
    """Aceptar el retraso (§4.6.4): el plan es la reproyección; el costo es el indirecto
    `CF' - CF` más `penalizacion diaria × días de retraso`."""
    return _cerrar(contexto, "aceptar", contexto.base, CERO, (), {})


def opciones(contexto: ContextoRecuperacion) -> tuple[Opcion, ...]:
    """Las cuatro opciones, en el orden de `OPCIONES`."""
    return (
        opcion_cuadrillas(contexto),
        opcion_horas_extra(contexto),
        opcion_paralelo(contexto),
        opcion_aceptar(contexto),
    )
