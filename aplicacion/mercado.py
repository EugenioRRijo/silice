"""El estudio de mercado: observaciones, estadísticas, piso y propuesta (MP-5, Tarea 13).

Diseño de montar un presupuesto §5.1 y §10, con las decisiones que Eugenio ratificó el 2026-10-25:

- Las observaciones son **datos de la empresa** y viven en la carpeta de trabajo
  (`aplicacion/tablas_mercado.py`). Se cuentan en la moneda de la carpeta (D-MP1): las de otra
  moneda no se mezclan, solo se cuentan aparte (`otras_monedas`). El precio tecleado se lee con
  `cifra_escrita` (coma decimal, punto de miles).
- Ventana: las observaciones con `hoy − dias <= fecha <= hoy` (90 días por omisión, cambiable).
- Cuartiles como `CUARTIL.INC` de Excel (interpolación lineal tipo 7): sobre los precios ordenados,
  posición `(n − 1)·p`. Las cifras de `Estadisticas` son **exactas**; se muestran en céntimos con
  `centimos` (`ROUND_HALF_UP`). Las comparaciones con el piso se hacen con las exactas.
- Piso de cobro (no perder dinero) = costo directo + administración del APU de la partida con la
  lista para armar, con los parámetros de la versión vigente de la obra abierta (o los por omisión
  de `ParametrosCosto`); el margen se mide contra el precio unitario con utilidad, sin IVA.
- Propuesta, nunca decisión: para compras, la mediana (y la más barata vista); para cobro, el
  primer cuartil si es igual o mayor que el piso, si no el piso, y lo dice. El precio propuesto va
  en céntimos y el de cobro nunca queda por debajo del piso por el redondeo (se redondea hacia
  arriba lo que haga falta).

Todo determinista, sin IA. Ninguna función confirma: escriben con `flush` y quien llama confirma.
Los mensajes en oraciones con mayúscula son los que ve la persona.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from aplicacion.cifras import cifra_escrita, texto_de_cifra
from aplicacion.listas_para_armar import lista_para_armar, moneda_de_la_carpeta
from aplicacion.tablas_mercado import ObservacionDeMercado
from core import models
from core.budget.edicion import version_vigente
from core.catalog import Catalogo
from core.contracts.apu import ParametrosCosto
from core.costing import calcular_apu

__all__ = [
    "DIAS_POR_OMISION",
    "FUENTES",
    "LADOS",
    "CarpetaSinMoneda",
    "Estadisticas",
    "Propuesta",
    "centimos",
    "estadisticas",
    "margen",
    "piso_de_cobro",
    "propuesta",
    "registrar_observacion",
]

#: «Lo que compramos» (insumos) y «Lo que cobramos» (partidas).
LADOS = ("compra", "cobro")
#: De dónde sale un precio observado.
FUENTES = ("proveedor", "competidor", "cotizacion", "maprex", "compra")
DIAS_POR_OMISION = 90

MENSAJE_SIN_MONEDA = (
    "Esta carpeta de trabajo aún no tiene moneda: declárela o cree su lista para armar antes de "
    "estudiar el mercado."
)
_LARGO_FUENTE = 200
_LARGO_NOTA = 500
_LARGO_RESPONSABLE = 200
_CENTIMO = Decimal("0.01")
_DECIMA = Decimal("0.1")
_CIEN = Decimal(100)
_Q1 = Decimal("0.25")
_MEDIANA = Decimal("0.5")


class CarpetaSinMoneda(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """La carpeta no tiene moneda declarada ni lista vigente: no hay en qué contar los precios."""


@dataclass(frozen=True)
class Estadisticas:
    """Las cifras de las observaciones que cuentan (exactas; `None` sin observaciones).

    `ids` son las observaciones de las que salen (ordenadas); `otras_monedas`, las de la ventana
    que están en otra moneda y no se mezclan; `dias`, la ventana usada."""

    moneda: str
    n: int
    minimo: Decimal | None
    q1: Decimal | None
    mediana: Decimal | None
    promedio: Decimal | None
    maximo: Decimal | None
    ids: tuple[int, ...]
    otras_monedas: int
    dias: int


@dataclass(frozen=True)
class Propuesta:
    """El precio que Sílice propone (en céntimos; `None` sin observaciones), por qué, y el piso
    exacto con que se comparó (`None` en compras, que no tienen piso)."""

    precio: Decimal | None
    razon: str
    piso: Decimal | None


# --- utilidades -------------------------------------------------------------------------------


def centimos(valor: Decimal | None) -> Decimal | None:
    """`valor` como se muestra: a 0,01 con la mitad hacia arriba (`None` sigue siendo `None`)."""
    return None if valor is None else valor.quantize(_CENTIMO, rounding=ROUND_HALF_UP)


def _exigir_lado(lado: str) -> None:
    if lado not in LADOS:
        raise ValueError(f"lado {lado!r}; se espera compra o cobro")


def _exigir_moneda(sesion: Session, fecha: date) -> str:
    moneda = moneda_de_la_carpeta(sesion, fecha)
    if moneda is None:
        raise CarpetaSinMoneda(MENSAJE_SIN_MONEDA)
    return moneda


def _texto_acotado(valor: str, largo: int, nombre: str) -> str:
    valor = valor.strip()
    if len(valor) > largo:
        raise ValueError(f"La {nombre} admite hasta {largo} caracteres.")
    return valor


def _existe(sesion: Session, lado: str, codigo: str) -> bool:
    if lado == "compra":
        condicion = exists().where(models.Insumo.codigo == codigo)
    else:
        condicion = exists().where(models.Partida.codigo == codigo)
    return bool(sesion.scalar(select(condicion)))


def _sin_partida(codigo: str) -> str:
    return f"No hay ninguna partida «{codigo}» en el catálogo de esta carpeta de trabajo."


# --- registrar --------------------------------------------------------------------------------


def registrar_observacion(
    sesion: Session,
    *,
    lado: str,
    codigo: str,
    fuente_tipo: str,
    fuente: str,
    fecha: date,
    precio: str,
    nota: str,
    responsable: str,
    ahora: datetime,
) -> int:
    """Anota un precio visto en el mercado y devuelve su `id`.

    `precio` es el texto tal como lo tecleó la persona (`CifraInvalida` si no sigue la regla) y
    debe ser mayor que cero; la moneda es la de la carpeta (`CarpetaSinMoneda` si no la tiene).
    `codigo` es un insumo de la carpeta (compra) o una partida de su catálogo (cobro). La fecha no
    puede ser posterior a `ahora`. `ValueError` con el mensaje para la persona en lo demás. No
    confirma."""
    _exigir_lado(lado)
    if fuente_tipo not in FUENTES:
        raise ValueError(
            f"fuente_tipo {fuente_tipo!r}; se espera proveedor, competidor, cotizacion, maprex o "
            "compra"
        )
    responsable = responsable.strip()
    if not responsable:
        raise ValueError("hace falta quién lo hace (responsable)")
    fuente = _texto_acotado(fuente, _LARGO_FUENTE, "fuente")
    if not fuente:
        raise ValueError("Escriba de dónde sale el precio (la fuente).")
    nota = _texto_acotado(nota, _LARGO_NOTA, "nota")
    valor = cifra_escrita(precio)
    if valor <= 0:
        raise ValueError("El precio debe ser mayor que cero.")
    if fecha > ahora.date():
        raise ValueError("La fecha de la observación no puede ser posterior a hoy.")
    moneda = _exigir_moneda(sesion, ahora.date())
    codigo = codigo.strip()
    if not _existe(sesion, lado, codigo):
        if lado == "compra":
            raise ValueError(f"No hay ningún insumo «{codigo}» en esta carpeta de trabajo.")
        raise ValueError(_sin_partida(codigo))
    fila = ObservacionDeMercado(
        lado=lado,
        codigo=codigo,
        fuente_tipo=fuente_tipo,
        fuente=fuente,
        fecha=fecha,
        moneda=moneda,
        precio=valor,
        nota=nota,
        responsable=responsable[:_LARGO_RESPONSABLE],
        fecha_hora=ahora,
        anulada_por=None,
    )
    sesion.add(fila)
    sesion.flush()
    return fila.id


# --- estadísticas -----------------------------------------------------------------------------


def _cuartil_inc(ordenados: list[Decimal], p: Decimal) -> Decimal:
    """`CUARTIL.INC` de Excel: interpolación lineal en la posición `(n − 1)·p` (desde 0)."""
    posicion = (len(ordenados) - 1) * p
    abajo = int(posicion)  # posición >= 0: truncar es el piso
    fraccion = posicion - abajo
    if fraccion == 0:
        return ordenados[abajo]
    return ordenados[abajo] + fraccion * (ordenados[abajo + 1] - ordenados[abajo])


def estadisticas(
    sesion: Session, *, lado: str, codigo: str, hoy: date, dias: int = DIAS_POR_OMISION
) -> Estadisticas:
    """n, mínimo, primer cuartil, mediana, promedio y máximo de las observaciones vigentes (no
    anuladas) de `codigo` en la moneda de la carpeta, con fecha entre `hoy − dias` y `hoy`."""
    _exigir_lado(lado)
    if dias < 0:
        raise ValueError(f"dias {dias}; se espera 0 o más")
    moneda = _exigir_moneda(sesion, hoy)
    filas = sesion.scalars(
        select(ObservacionDeMercado)
        .where(
            ObservacionDeMercado.lado == lado,
            ObservacionDeMercado.codigo == codigo,
            ObservacionDeMercado.anulada_por.is_(None),
            ObservacionDeMercado.fecha >= hoy - timedelta(days=dias),
            ObservacionDeMercado.fecha <= hoy,
        )
        .order_by(ObservacionDeMercado.id)
    ).all()
    cuentan = [f for f in filas if f.moneda == moneda]
    otras = len(filas) - len(cuentan)
    ids = tuple(f.id for f in cuentan)
    if not cuentan:
        return Estadisticas(moneda, 0, None, None, None, None, None, ids, otras, dias)
    precios = sorted(f.precio for f in cuentan)
    return Estadisticas(
        moneda=moneda,
        n=len(precios),
        minimo=precios[0],
        q1=_cuartil_inc(precios, _Q1),
        mediana=_cuartil_inc(precios, _MEDIANA),
        promedio=sum(precios, Decimal(0)) / len(precios),
        maximo=precios[-1],
        ids=ids,
        otras_monedas=otras,
        dias=dias,
    )


# --- piso ---------------------------------------------------------------------------------------


def _parametros(sesion: Session, proyecto: str | None, moneda: str) -> ParametrosCosto:
    """Los de la versión vigente de la obra; sin obra o sin versión, los por omisión.

    El bono de alimentación es un monto en la moneda de la versión: si la obra está en otra moneda
    que la carpeta, no se mezcla y se usa el de omisión (los factores sí valen)."""
    if proyecto is None:
        return ParametrosCosto()
    existe = sesion.scalar(select(exists().where(models.Proyecto.nombre == proyecto)))
    if not existe:
        raise ValueError(f"No hay ninguna obra «{proyecto}» en esta carpeta de trabajo.")
    vigente = version_vigente(sesion, proyecto)
    if vigente is None:
        return ParametrosCosto()
    bono = (
        vigente.bono_alimentacion
        if vigente.moneda == moneda
        else ParametrosCosto().bono_alimentacion
    )
    return ParametrosCosto(
        fcas=vigente.fcas,
        bono_alimentacion=bono,
        administracion=vigente.administracion,
        utilidad=vigente.utilidad,
    )


def piso_de_cobro(
    sesion: Session,
    catalogo: Catalogo,
    codigo_partida: str,
    *,
    proyecto: str | None,
    fecha: date,
) -> tuple[Decimal, Decimal]:
    """(piso, precio unitario) de la partida, exactos: el APU con la lista para armar a `fecha`;
    el piso es costo directo + administración y el precio unitario lleva además la utilidad (sin
    IVA). `SinListaParaArmar` sin lista en la moneda de la carpeta; `ValueError` si la obra o la
    partida no existen."""
    lista = lista_para_armar(sesion, fecha)
    parametros = _parametros(sesion, proyecto, lista.moneda)
    try:
        composicion = catalogo.composicion(codigo_partida, fecha=fecha, lista=lista)
    except KeyError:
        raise ValueError(_sin_partida(codigo_partida)) from None
    resultado = calcular_apu(composicion, parametros)
    return resultado.con_administracion, resultado.precio_unitario


# --- propuesta y margen -------------------------------------------------------------------------


def _observaciones(n: int) -> str:
    return "1 observación" if n == 1 else f"{n} observaciones"


def propuesta(lado: str, est: Estadisticas, piso: Decimal | None) -> Propuesta:
    """Lo que Sílice propone; la persona decide siempre."""
    _exigir_lado(lado)
    if lado == "compra" and piso is not None:
        raise ValueError("lo que se compra no tiene piso")
    if lado == "cobro" and piso is None:
        raise ValueError("lo que se cobra necesita su piso")
    if est.n == 0:
        return Propuesta(None, f"Sin observaciones en los últimos {est.dias} días.", piso)
    assert est.mediana is not None and est.minimo is not None and est.q1 is not None
    if lado == "compra":
        barata = texto_de_cifra(centimos(est.minimo))  # type: ignore[arg-type]
        return Propuesta(
            precio=centimos(est.mediana),
            razon=(
                f"Mediana de {_observaciones(est.n)}; la más barata vista: {barata} {est.moneda}."
            ),
            piso=None,
        )
    assert piso is not None
    minimo_sin_perder = piso.quantize(_CENTIMO, rounding=ROUND_CEILING)
    if est.q1 >= piso:
        mostrado = centimos(est.q1)
        assert mostrado is not None
        return Propuesta(
            precio=max(mostrado, minimo_sin_perder),
            razon="Primer cuartil del mercado, por encima de su costo.",
            piso=piso,
        )
    return Propuesta(
        precio=minimo_sin_perder,
        razon="La competencia cobra menos que su costo: se propone su costo.",
        piso=piso,
    )


def margen(objetivo: Decimal, precio_unitario: Decimal) -> Decimal:
    """(objetivo − precio unitario) / precio unitario, en porcentaje con una cifra decimal
    (`ROUND_HALF_UP`): negativo si el objetivo queda por debajo del precio con utilidad."""
    if precio_unitario <= 0:
        raise ValueError("el precio unitario debe ser mayor que cero")
    porcentaje = (objetivo - precio_unitario) / precio_unitario * _CIEN
    return porcentaje.quantize(_DECIMA, rounding=ROUND_HALF_UP)
