"""Proyección del riesgo de precios de una obra (plan vial, Tarea 13; especificación §5.1, 2 y 3).

**Método: remuestreo de meses históricos completos** (prácticas AACE 58R-10 y 68R-11, que la tesis
cita; especificación §6 deja el muestreo al constructor siempre que sea reproducible):

1. **Meses completos.** La ventana son los `ventana_meses` meses anteriores al mes de `inicio` (el
   mes de inicio y lo posterior no se ven). Un mes `m` es completo si **todas** las series que
   intervienen (las del mapa y la tasa BCV) tienen valor en `m` y en `m − 1`: su variación es
   `valor[m] / valor[m − 1]`. Un mes sin dato en una sola serie se descarta para todas, así que un
   hueco en medio cuesta dos variaciones (la del mes y la del siguiente). Con menos de
   `MINIMO_DE_MESES` meses completos no se proyecta (foco de revisión 4).
2. **Trayectorias.** Por trayectoria se eligen `meses` meses completos con reemplazo, **el mismo
   mes histórico para todas las series** (conserva su correlación, también con la tasa). El
   multiplicador de la serie en el mes `k` del plazo es el producto de sus variaciones hasta `k`.
3. **Gasto uniforme (D-V-3).** El factor de un insumo es el promedio de sus multiplicadores en los
   `meses` del plazo.
4. **Moneda.** Todas las composiciones están en la moneda del presupuesto. Las series viales
   (`SERIES_VIALES`) son en USD: en un presupuesto en Bs su multiplicador se compone con el de la
   tasa **del mismo mes** antes de promediar. Un insumo sin serie, en un presupuesto en Bs, es «USD
   fijo × tasa»; en uno en USD queda fijo. Una serie que no es vial ni la tasa se rechaza: no se
   sabe en qué moneda está.
5. **Mezcla propia.** Su receta se recalcula en cada trayectoria con `costo_de_mezcla` (Tarea 4):
   cada componente a su precio base por su factor (con su serie si está en el mapa por su código;
   si no, la regla del insumo sin serie) y la planta con la regla del insumo sin serie. El precio
   de la mezcla en el presupuesto se escala por `costo simulado / costo base`, así una mezcla
   publicada de otro período no salta solo por recalcularla.
6. **Total.** Cada trayectoria revaloriza con `core.budget.escenarios.generar_escenario` (sin
   auditar: el informe es del presupuesto base). Percentiles por el método **del más cercano por
   rango**; reserva = P80 − total base (D-V-3), sin recortar si sale negativa.
7. **Contribución.** Por insumo, el total con solo ese insumo a su factor medio menos el total base
   (es «cantidad × precio × (factor medio − 1)» con la administración y la utilidad del motor);
   de mayor a menor, sin los que no se movieron.

**Reproducible.** `random.Random(semilla)` y solo su método `random()`, el único cuya secuencia
Python garantiza entre versiones para la misma semilla. Todo en `Decimal` con 28 cifras y redondeo
de mitad al par; se redondea solo al presentar. La IA nunca calcula estas cifras.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from sqlalchemy.orm import Session

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from aplicacion.riesgo.series import SERIES_VIALES, MapaSeries, historia_mensual
from core.budget.escenarios import generar_escenario
from core.catalog.indices import LADO_POR_DEFECTO, definicion_tasa
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from produccion.costo import costo_de_mezcla
from produccion.fuentes import CIFRAS_DEL_CALCULO
from produccion.receta import Receta

__all__ = [
    "HORIZONTE_MESES",
    "MINIMO_DE_MESES",
    "SERIE_TASA",
    "TRAYECTORIAS",
    "VENTANA_MESES",
    "ParametrosProyeccion",
    "Proyeccion",
    "historia_para_proyectar",
    "percentil_mas_cercano_por_rango",
    "meses_completos",
    "proyectar",
    "series_del_mapa",
    "total_con_variaciones_reales",
]

FUENTE_D_V_3 = "D-V-3, decisión por defecto del plan vial (aprobada por Eugenio el 2026-10-30)"
TRAYECTORIAS = Constante("RV-1", "Trayectorias por proyección", Decimal(2000), FUENTE_D_V_3)
VENTANA_MESES = Constante("RV-2", "Meses de historia en la ventana", Decimal(36), FUENTE_D_V_3)
HORIZONTE_MESES = Constante("RV-3", "Meses del plazo proyectado", Decimal(6), FUENTE_D_V_3)
#: Foco de revisión 4 del plan vial: con menos meses completos no se proyecta.
MINIMO_DE_MESES = Constante(
    "RV-4", "Meses completos mínimos para proyectar", Decimal(12), SUPUESTO_DECLARADO
)
PERCENTILES_POR_DEFECTO = (50, 80)
PERCENTIL_DE_LA_RESERVA = 80

#: La tasa BCV del lado por defecto (venta): la serie que ya existe, no una nueva.
SERIE_TASA = definicion_tasa(LADO_POR_DEFECTO).codigo
SERIES_EN_USD = frozenset(s.codigo for s in SERIES_VIALES)
MONEDAS = ("Bs", "USD")
UNO = Decimal(1)
CERO = Decimal(0)


def _contexto():
    return localcontext(prec=CIFRAS_DEL_CALCULO, rounding=ROUND_HALF_EVEN)


def _entero(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


@dataclass(frozen=True)
class ParametrosProyeccion:
    inicio: date
    meses: int = int(HORIZONTE_MESES.valor)
    semilla: int = 1
    trayectorias: int = int(TRAYECTORIAS.valor)
    ventana_meses: int = int(VENTANA_MESES.valor)
    percentiles: tuple[int, ...] = PERCENTILES_POR_DEFECTO

    def __post_init__(self) -> None:
        if not isinstance(self.inicio, date) or isinstance(self.inicio, datetime):
            raise ValueError("el inicio de la proyección debe ser una fecha")
        if not _entero(self.meses) or self.meses < 1:
            raise ValueError("los meses del plazo deben ser un entero mayor que cero")
        if not _entero(self.trayectorias) or self.trayectorias < 1:
            raise ValueError("las trayectorias deben ser un entero mayor que cero")
        if not _entero(self.semilla):
            raise ValueError("la semilla debe ser un entero")
        minimo = int(MINIMO_DE_MESES.valor)
        if not _entero(self.ventana_meses) or self.ventana_meses < minimo:
            raise ValueError(f"la ventana debe tener al menos {minimo} meses")
        object.__setattr__(self, "percentiles", tuple(self.percentiles))
        if any(not _entero(p) or not 1 <= p <= 100 for p in self.percentiles):
            raise ValueError("cada percentil debe ser un entero entre 1 y 100")
        if len(set(self.percentiles)) != len(self.percentiles):
            raise ValueError("hay un percentil repetido")
        if PERCENTIL_DE_LA_RESERVA not in self.percentiles:
            raise ValueError("la reserva es P80 − total base: los percentiles deben incluir el 80")


@dataclass(frozen=True)
class Proyeccion:
    total_base: Decimal
    percentiles: dict[int, Decimal]
    reserva: Decimal
    contribucion: tuple[tuple[str, Decimal], ...]
    meses_usados: int
    semilla: int
    supuestos: tuple[str, ...]


# --- Meses ----------------------------------------------------------------------------------------


def _mes(base: date, desplazamiento: int) -> date:
    """El primer día del mes `desplazamiento` meses después (o antes) del de `base`."""
    indice = base.year * 12 + base.month - 1 + desplazamiento
    return date(indice // 12, indice % 12 + 1, 1)


def historia_para_proyectar(
    sesion: Session, mapa: MapaSeries, p: ParametrosProyeccion
) -> dict[str, dict[date, Decimal]]:
    """La historia mensual que necesita `proyectar`: las series del mapa y la tasa, desde el mes
    anterior a la ventana (base de su primera variación) hasta el **último día del mes anterior al
    inicio**, así ningún mes queda a medias (fila 75 de las preguntas para Eugenio)."""
    inicio = p.inicio.replace(day=1)
    codigos = sorted(set(mapa.serie_por_insumo.values()) | {SERIE_TASA})
    desde = _mes(inicio, -(p.ventana_meses + 1))
    return historia_mensual(sesion, codigos, desde, inicio - timedelta(days=1))


def meses_completos(
    historia: Mapping[str, Mapping[date, Decimal]], series: Sequence[str], p: ParametrosProyeccion
) -> list[date]:
    """Los meses completos de la ventana de `p`: los `ventana_meses` anteriores al mes de
    `p.inicio` con valor en ese mes y en el anterior en todas las `series` (la comprobación hacia
    atrás los cuenta por corte con esta misma regla)."""
    inicio = p.inicio.replace(day=1)
    ventana = [_mes(inicio, -i) for i in range(p.ventana_meses, 0, -1)]
    return [
        m
        for m in ventana
        if all(m in historia.get(s, {}) and _mes(m, -1) in historia.get(s, {}) for s in series)
    ]


def _variaciones(
    historia: Mapping[str, Mapping[date, Decimal]], series: Sequence[str], p: ParametrosProyeccion
) -> tuple[list[date], dict[str, list[Decimal]]]:
    """Los meses completos de la ventana y, por serie, su variación en cada uno."""
    completos = meses_completos(historia, series, p)
    minimo = int(MINIMO_DE_MESES.valor)
    if len(completos) < minimo:
        raise ValueError(f"solo hay {len(completos)} meses completos; se necesitan {minimo}")
    variaciones: dict[str, list[Decimal]] = {}
    for s in series:
        valores = historia[s]
        for m in completos:
            for mes in (_mes(m, -1), m):
                if not valores[mes] > CERO:
                    raise ValueError(f"la serie {s} tiene un valor no positivo en {mes:%m/%Y}")
        variaciones[s] = [valores[m] / valores[_mes(m, -1)] for m in completos]
    return completos, variaciones


def _variaciones_reales(
    historia: Mapping[str, Mapping[date, Decimal]], series: Sequence[str], inicio: date, meses: int
) -> dict[str, list[Decimal]]:
    """Las variaciones que de verdad ocurrieron en los `meses` meses desde `inicio` (el mes de
    inicio incluido), por serie y en orden. Se niega si a una serie le falta un valor."""
    primero = inicio.replace(day=1)
    variaciones: dict[str, list[Decimal]] = {}
    for s in series:
        valores = historia.get(s, {})
        lista = []
        for k in range(meses):
            m = _mes(primero, k)
            for mes in (_mes(m, -1), m):
                if mes not in valores:
                    raise ValueError(f"a la serie {s} le falta el valor de {mes:%m/%Y}")
                if not valores[mes] > CERO:
                    raise ValueError(f"la serie {s} tiene un valor no positivo en {mes:%m/%Y}")
            lista.append(valores[m] / valores[_mes(m, -1)])
        variaciones[s] = lista
    return variaciones


# --- Precios y factores ---------------------------------------------------------------------------


def _precios_base(composiciones: Mapping[str, ComposicionAPU]) -> dict[str, Decimal]:
    """El precio de cada insumo por su descripción (como lo indexa `generar_escenario`). Un insumo
    con dos precios distintos se niega: el escenario lo variaría con uno solo."""
    precios: dict[str, Decimal] = {}
    for apu in composiciones.values():
        lineas = [(x.descripcion, x.precio) for x in (*apu.materiales, *apu.equipos)]
        lineas += [(x.descripcion, x.sueldo) for x in apu.mano_obra]
        for descripcion, precio in lineas:
            anterior = precios.setdefault(descripcion, precio)
            if anterior != precio:
                raise ValueError(
                    f"el insumo «{descripcion}» tiene dos precios en las composiciones "
                    f"({anterior} y {precio}): la proyección lo variaría con uno solo"
                )
    return precios


@dataclass(frozen=True)
class _Mezcla:
    receta: Receta
    planta: Decimal
    costo_base: Decimal


def _mezclas(
    recetas: Mapping[str, Receta],
    costo_planta_por_t: Mapping[str, Decimal],
    precio_de_componente: Mapping[str, Decimal],
    precios: Mapping[str, Decimal],
    mapa: MapaSeries,
) -> dict[str, _Mezcla]:
    mezclas: dict[str, _Mezcla] = {}
    for descripcion, receta in recetas.items():
        if descripcion not in precios:
            raise ValueError(f"la mezcla «{descripcion}» tiene receta pero no está en ningún APU")
        if descripcion in mapa.serie_por_insumo:
            raise ValueError(
                f"la mezcla «{descripcion}» tiene receta y serie: se recalcula con su receta, "
                "quite su serie del mapa"
            )
        if descripcion not in costo_planta_por_t:
            raise ValueError(f"falta el costo de planta por tonelada de «{descripcion}»")
        planta = costo_planta_por_t[descripcion]
        costo = costo_de_mezcla(receta, precio_de_componente, precio_de_componente, planta)
        if not costo > CERO:
            raise ValueError(f"el costo base de la mezcla «{descripcion}» no es mayor que cero")
        mezclas[descripcion] = _Mezcla(receta, planta, costo)
    return mezclas


def series_del_mapa(mapa: MapaSeries) -> list[str]:
    """Las series que intervienen en una proyección: las del mapa y la tasa BCV, ordenadas."""
    return sorted(set(mapa.serie_por_insumo.values()) | {SERIE_TASA})


def _validar_series(mapa: MapaSeries, moneda: str) -> None:
    desconocidas = sorted(set(mapa.serie_por_insumo.values()) - SERIES_EN_USD - {SERIE_TASA})
    if desconocidas:
        raise ValueError(
            f"no se sabe en qué moneda está la serie {', '.join(desconocidas)}: la proyección "
            f"admite las series viales en USD ({', '.join(sorted(SERIES_EN_USD))}) y la tasa "
            f"{SERIE_TASA}"
        )
    if moneda == "USD":
        con_tasa = sorted(i for i, s in mapa.serie_por_insumo.items() if s == SERIE_TASA)
        if con_tasa:
            raise ValueError(
                f"en un presupuesto en USD un insumo no puede seguir a la tasa {SERIE_TASA} "
                f"(su precio en USD bajaría al subir la tasa): {', '.join(con_tasa)}"
            )


class _Trayectoria:
    """Los multiplicadores acumulados de cada serie en cada mes del plazo, y el factor medio
    (gasto uniforme) de un insumo según su serie y la moneda del presupuesto."""

    def __init__(self, acumulados: dict[str, list[Decimal]], en_bs: bool) -> None:
        self._acumulados = acumulados
        self._en_bs = en_bs
        self._cache: dict[str | None, Decimal] = {}

    def factor(self, serie: str | None) -> Decimal:
        if serie not in self._cache:
            tasa = self._acumulados[SERIE_TASA]
            if serie is None:
                mensual = tasa if self._en_bs else [UNO] * len(tasa)
            elif serie == SERIE_TASA or not self._en_bs:
                mensual = self._acumulados[serie]
            else:  # serie en USD en un presupuesto en Bs: se compone con la tasa del mismo mes
                mensual = [a * t for a, t in zip(self._acumulados[serie], tasa, strict=True)]
            self._cache[serie] = sum(mensual, CERO) / len(mensual)
        return self._cache[serie]


def _trayectoria(
    rng: random.Random, variaciones: dict[str, list[Decimal]], meses: int, en_bs: bool
) -> _Trayectoria:
    n = len(next(iter(variaciones.values())))
    elegidos = [int(rng.random() * n) for _ in range(meses)]  # el mismo mes para todas las series
    return _acumulada({s: [v[i] for i in elegidos] for s, v in variaciones.items()}, en_bs)


def _acumulada(variaciones_del_plazo: Mapping[str, Sequence[Decimal]], en_bs: bool) -> _Trayectoria:
    """La trayectoria que sigue estas variaciones, mes a mes del plazo (las remuestreadas o las
    reales: el factor sale por la misma regla)."""
    acumulados: dict[str, list[Decimal]] = {}
    for serie, valores in variaciones_del_plazo.items():
        acumulado, lista = UNO, []
        for v in valores:
            acumulado *= v
            lista.append(acumulado)
        acumulados[serie] = lista
    return _Trayectoria(acumulados, en_bs)


def _factores(
    t: _Trayectoria,
    precios: Mapping[str, Decimal],
    mapa: MapaSeries,
    mezclas: Mapping[str, _Mezcla],
    precio_de_componente: Mapping[str, Decimal],
) -> dict[str, Decimal]:
    serie = mapa.serie_por_insumo
    factores = {d: t.factor(serie.get(d)) for d in precios if d not in mezclas}
    for descripcion, m in mezclas.items():
        componentes = {
            c.codigo: precio_de_componente[c.codigo] * t.factor(serie.get(c.codigo))
            for c in m.receta.componentes
        }
        simulado = costo_de_mezcla(m.receta, componentes, componentes, m.planta * t.factor(None))
        factores[descripcion] = simulado / m.costo_base
    return factores


def percentil_mas_cercano_por_rango(valores: Sequence[Decimal], p: int) -> Decimal:
    """Percentil `p` por el método **del más cercano por rango**: el valor de rango ⌈p/100 × N⌉
    (contando desde 1) de los `N` valores ordenados de menor a mayor. Siempre es uno de los
    valores (no interpola) y se calcula con enteros, sin flotantes."""
    if not valores:
        raise ValueError("no hay valores de los que sacar un percentil")
    if not _entero(p) or not 1 <= p <= 100:
        raise ValueError("el percentil debe ser un entero entre 1 y 100")
    ordenados = sorted(valores)
    rango = -(-p * len(ordenados) // 100)  # techo entero de p × N / 100
    return ordenados[rango - 1]


class _Motor:
    """Lo que comparten `proyectar` y `total_con_variaciones_reales`: los precios base, las
    mezclas con receta, el total por el motor del núcleo y los factores de una trayectoria. Se
    construye dentro de `_contexto()`. Valida la moneda, las series y que las composiciones
    reproduzcan el total del presupuesto."""

    def __init__(
        self,
        presupuesto: Presupuesto,
        composiciones: Mapping[str, ComposicionAPU],
        parametros_costo: ParametrosCosto,
        mapa: MapaSeries,
        recetas: Mapping[str, Receta],
        costo_planta_por_t: Mapping[str, Decimal],
        precio_de_componente: Mapping[str, Decimal],
    ) -> None:
        if presupuesto.moneda not in MONEDAS:
            raise ValueError(f"moneda del presupuesto {presupuesto.moneda!r}; se espera Bs o USD")
        _validar_series(mapa, presupuesto.moneda)
        self._presupuesto = presupuesto
        self._composiciones = composiciones
        self._parametros_costo = parametros_costo
        self._mapa = mapa
        self._precio_de_componente = precio_de_componente
        self.series = series_del_mapa(mapa)
        self.precios = _precios_base(composiciones)
        self.mezclas = _mezclas(
            recetas, costo_planta_por_t, precio_de_componente, self.precios, mapa
        )
        recalculado = self.total({}, "base")
        if recalculado != presupuesto.total:
            raise ValueError(
                f"las composiciones y los parámetros no reproducen el total del presupuesto "
                f"({recalculado} frente a {presupuesto.total}): la proyección compararía cosas "
                "distintas"
            )

    def total(self, con: Mapping[str, Decimal], nombre: str) -> Decimal:
        escenario = generar_escenario(
            nombre,
            self._presupuesto,
            self._composiciones,
            self._parametros_costo,
            precios=con,
            reglas=(),
        )
        return escenario.presupuesto.total

    def factores(self, t: _Trayectoria) -> dict[str, Decimal]:
        return _factores(t, self.precios, self._mapa, self.mezclas, self._precio_de_componente)


def total_con_variaciones_reales(
    presupuesto: Presupuesto,
    composiciones: Mapping[str, ComposicionAPU],
    parametros_costo: ParametrosCosto,
    historia: Mapping[str, Mapping[date, Decimal]],
    mapa: MapaSeries,
    inicio: date,
    meses: int,
    *,
    recetas: Mapping[str, Receta] | None = None,
    costo_planta_por_t: Mapping[str, Decimal] | None = None,
    precio_de_componente: Mapping[str, Decimal] | None = None,
) -> Decimal:
    """El total del presupuesto revalorizado con lo que **de verdad pasó** en los `meses` meses
    desde `inicio` (el mes de inicio incluido), por las mismas reglas que `proyectar`: el
    multiplicador de cada serie en el mes `k` del plazo es el producto de sus variaciones reales
    hasta `k`, el factor de cada insumo es el promedio de sus multiplicadores (gasto uniforme), y
    valen la misma regla de la moneda y la misma recomposición de la mezcla. Es el valor contra el
    que la comprobación hacia atrás compara el P80. Pide el valor de cada serie desde el mes
    anterior a `inicio` hasta el último mes del plazo."""
    if not _entero(meses) or meses < 1:
        raise ValueError("los meses del plazo deben ser un entero mayor que cero")
    with _contexto():
        motor = _Motor(
            presupuesto,
            composiciones,
            parametros_costo,
            mapa,
            recetas or {},
            costo_planta_por_t or {},
            precio_de_componente or {},
        )
        reales = _variaciones_reales(historia, motor.series, inicio, meses)
        factores = motor.factores(_acumulada(reales, presupuesto.moneda == "Bs"))
        return motor.total({d: motor.precios[d] * f for d, f in factores.items()}, "real")


# --- La proyección --------------------------------------------------------------------------------


def proyectar(
    presupuesto: Presupuesto,
    composiciones: Mapping[str, ComposicionAPU],
    parametros_costo: ParametrosCosto,
    historia: Mapping[str, Mapping[date, Decimal]],
    mapa: MapaSeries,
    p: ParametrosProyeccion,
    *,
    recetas: Mapping[str, Receta] | None = None,
    costo_planta_por_t: Mapping[str, Decimal] | None = None,
    precio_de_componente: Mapping[str, Decimal] | None = None,
) -> Proyeccion:
    """Percentiles del total de `presupuesto` en el plazo, la reserva y qué insumos empujan.

    `historia` es la de `historia_para_proyectar` (`{serie: {primer día del mes: valor}}`). Las
    claves de `recetas` y `costo_planta_por_t` son la **descripción** del insumo de la mezcla en
    las composiciones; `precio_de_componente` da el precio base de cada componente de las recetas
    por su **código** (en la moneda del presupuesto), y el mapa puede dar la serie de un
    componente por ese mismo código. Las reglas del método están en el encabezado del módulo."""
    with _contexto():
        motor = _Motor(
            presupuesto,
            composiciones,
            parametros_costo,
            mapa,
            recetas or {},
            costo_planta_por_t or {},
            precio_de_componente or {},
        )
        precios, mezclas, total = motor.precios, motor.mezclas, motor.total
        completos, variaciones = _variaciones(historia, motor.series, p)

        rng = random.Random(p.semilla)
        en_bs = presupuesto.moneda == "Bs"
        totales: list[Decimal] = []
        suma_de_factores = dict.fromkeys(precios, CERO)
        for n in range(p.trayectorias):
            t = _trayectoria(rng, variaciones, p.meses, en_bs)
            factores = motor.factores(t)
            for d, f in factores.items():
                suma_de_factores[d] += f
            totales.append(total({d: precios[d] * f for d, f in factores.items()}, f"t{n + 1}"))

        percentiles = {q: percentil_mas_cercano_por_rango(totales, q) for q in p.percentiles}
        contribucion = []
        for d, suma in suma_de_factores.items():
            medio = suma / p.trayectorias
            if medio != UNO:
                monto = total({d: precios[d] * medio}, f"solo {d}") - presupuesto.total
                if monto != CERO:
                    contribucion.append((d, monto))
        contribucion.sort(key=lambda par: (-par[1], par[0]))
        return Proyeccion(
            total_base=presupuesto.total,
            percentiles=percentiles,
            reserva=percentiles[PERCENTIL_DE_LA_RESERVA] - presupuesto.total,
            contribucion=tuple(contribucion),
            meses_usados=len(completos),
            semilla=p.semilla,
            supuestos=_supuestos(p, completos, en_bs, bool(mezclas)),
        )


def _supuestos(
    p: ParametrosProyeccion, completos: Sequence[date], en_bs: bool, hay_mezcla: bool
) -> tuple[str, ...]:
    supuestos = [
        f"gasto uniforme en el plazo: el factor de cada insumo es el promedio de sus "
        f"multiplicadores en los {p.meses} meses (D-V-3)",
        f"remuestreo de {len(completos)} meses completos (de {completos[0]:%m/%Y} a "
        f"{completos[-1]:%m/%Y}): el mismo mes histórico para todas las series y la tasa; "
        f"{p.trayectorias} trayectorias con semilla {p.semilla}",
        "percentiles por el método del más cercano por rango (rango ⌈p/100 × N⌉ de los totales "
        f"ordenados); reserva = P{PERCENTIL_DE_LA_RESERVA} − total base",
        "parámetros de costo fijos (FCAS, bono de alimentación, administración y utilidad): "
        "solo varían los precios de los insumos",
    ]
    if en_bs:
        supuestos += [
            f"insumo en Bs sin serie propia: USD fijo × tasa ({SERIE_TASA})",
            "serie en USD en un presupuesto en Bs: su variación se compone con la de la tasa del "
            "mismo mes",
        ]
    else:
        supuestos.append("insumo en USD sin serie propia: precio fijo")
    if hay_mezcla:
        supuestos.append(
            "mezcla propia recalculada con su receta en cada trayectoria; la planta sigue la "
            "regla del insumo sin serie; el precio de la mezcla se escala por costo simulado ÷ "
            "costo base"
        )
    return tuple(supuestos)
