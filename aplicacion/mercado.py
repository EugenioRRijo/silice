"""El estudio de mercado: observaciones, estadísticas, piso, propuesta y «Usar este precio» (MP-5,
Tareas 13 y 14).

Diseño de montar un presupuesto §5.1 y §10, con las decisiones que Eugenio ratificó el 2026-10-25:

- Las observaciones son **datos de la empresa** y viven en la carpeta de trabajo
  (`aplicacion/tablas_mercado.py`). Se cuentan en la moneda de la carpeta (D-MP1). Una observación
  en otra moneda **se cita convertida** (decisión de Eugenio del 2026-10-27, Tarea D3) con la tasa
  del BCV del mismo día de la observación (`aplicacion/tasa_del_dia.py`, D2b), con la misma
  `Equivalencia` que el precio del corte; entra en las cifras con el valor convertido. Sin tasa de
  ese día queda fuera de las cifras con «sin tasa del BCV del dd/mm/aaaa» y se cuenta aparte
  (`sin_tasa`). La observación original no se toca: se convierte al leer (la tasa queda en los
  índices, y la equivalencia reconstruye la cuenta). El precio tecleado se lee con `cifra_escrita`
  (coma decimal, punto de miles).
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
- Usar un precio de compra (D-MP2) lo escribe en la lista de hoy de la carpeta
  (`lista_de_hoy(..., nueva_si_usada=True)`: si una versión ya la usa, se deriva otra del mismo
  día, «… (2)») con su origen «Estudio de mercado…»; las versiones guardadas no cambian. Usar un
  precio de cobro guarda el precio de venta objetivo de la partida; vale el último.
- Anular una observación no la borra: se inserta un **contraasiento** (una fila que copia la
  observación, dice a cuál anula, quién y cuándo, y se anula a sí misma) y la observación queda con
  `anulada_por` = el contraasiento. Ninguna de las dos cuenta ni se lista.

Todo determinista, sin IA. Ninguna función confirma: escriben con `flush` y quien llama confirma.
Los mensajes que ve la persona van en `ReglaDeMercado` (lo escrito no cumple una regla) y en
`NoExiste` (lo pedido no está en la carpeta; la API lo da como 404); los demás `ValueError` son de
programación y la API no muestra su texto.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from aplicacion.cifras import cifra_escrita, texto_de_cifra
from aplicacion.listas_para_armar import (
    SinListaParaArmar,
    exigir_responsable,
    lista_de_hoy,
    lista_para_armar,
    moneda_de_la_carpeta,
)
from aplicacion.parametros_de_costo import parametros_de_version
from aplicacion.proyectos import proyectos_del_caso
from aplicacion.tablas_mercado import ObservacionDeMercado, PrecioObjetivo
from aplicacion.tasa_del_dia import Equivalencia, SinTasaDelDia, equivalencia_del_dia
from core import models
from core.budget.edicion import version_vigente
from core.catalog import Catalogo
from core.catalog.errores import CatalogoIncompleto
from core.contracts.apu import ParametrosCosto
from core.costing import calcular_apu

if TYPE_CHECKING:
    from aplicacion.mesa import Pendiente

__all__ = [
    "DIAS_POR_OMISION",
    "FUENTES",
    "LADOS",
    "MENSAJE_OBSERVACION_AJENA",
    "MENSAJE_SIN_MONEDA",
    "CarpetaSinMoneda",
    "Estadisticas",
    "NoExiste",
    "ObservacionAnulada",
    "Propuesta",
    "ReglaDeMercado",
    "anular_observacion",
    "apus_afectados",
    "centimos",
    "estadisticas",
    "exigir_codigo",
    "margen",
    "objetivos",
    "ObservacionLeida",
    "observaciones_leidas",
    "observaciones_vigentes",
    "pendientes_de_mercado",
    "piso_de_cobro",
    "propuesta",
    "registrar_observacion",
    "usar_precio_de_cobro",
    "usar_precio_de_compra",
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
MENSAJE_OBSERVACION_AJENA = (
    "La observación elegida no es un precio vigente de este insumo o partida."
)
RAZON_POR_ENCIMA = "Primer cuartil del mercado, igual o por encima de su costo."
RAZON_POR_DEBAJO = "La competencia cobra menos que su costo: se propone su costo."
FUENTE_DEL_PRECIO = "Estudio de mercado"
_LARGO_FUENTE = 200
_LARGO_NOTA = 500
_LARGO_RESPONSABLE = 200
#: Largo de `mp_precio_objetivo.observaciones` (los ids en JSON).
_LARGO_CITAS = 400
_CENTIMO = Decimal("0.01")
_DECIMA = Decimal("0.1")
_CIEN = Decimal(100)
_Q1 = Decimal("0.25")
_MEDIANA = Decimal("0.5")


class CarpetaSinMoneda(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """La carpeta no tiene moneda declarada ni lista vigente: no hay en qué contar los precios."""


class NoExiste(ValueError):  # noqa: N818
    """El insumo, la partida, la obra o la observación no está en esta carpeta; el mensaje es el
    que ve la persona."""


class ObservacionAnulada(ValueError):  # noqa: N818
    """La observación ya está anulada (o es el contraasiento de una anulación)."""


class ReglaDeMercado(ValueError):  # noqa: N818
    """Lo escrito no cumple una regla del estudio de mercado; el mensaje es el que ve la persona.
    Los demás `ValueError` de este módulo son errores de programación (lado, tipo de fuente,
    responsable) que la API no deja ver."""


@dataclass(frozen=True)
class Estadisticas:
    """Las cifras de las observaciones que cuentan (exactas; `None` sin observaciones).

    `ids` son las observaciones de las que salen (ordenadas); `convertidas`, cuántas de ellas
    estaban en otra moneda y entran convertidas; `sin_tasa`, las de la ventana en otra moneda a las
    que les falta la tasa del BCV de su día y por eso no entran; `dias`, la ventana usada."""

    moneda: str
    n: int
    minimo: Decimal | None
    q1: Decimal | None
    mediana: Decimal | None
    promedio: Decimal | None
    maximo: Decimal | None
    ids: tuple[int, ...]
    convertidas: int
    sin_tasa: int
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


def _responsable(texto: str) -> str:
    """Quién lo hace, sin blancos en los bordes; ni vacío ni más largo que la columna (no se
    recorta en silencio)."""
    responsable = exigir_responsable(texto)
    if len(responsable) > _LARGO_RESPONSABLE:
        raise ValueError(
            f"quien lo hace (responsable) admite hasta {_LARGO_RESPONSABLE} caracteres"
        )
    return responsable


def _texto_acotado(valor: str, largo: int, nombre: str) -> str:
    valor = valor.strip()
    if len(valor) > largo:
        raise ReglaDeMercado(f"La {nombre} admite hasta {largo} caracteres.")
    return valor


def _precio_positivo(precio: str) -> Decimal:
    valor = cifra_escrita(precio)
    if valor <= 0:
        raise ReglaDeMercado("El precio debe ser mayor que cero.")
    return valor


def _sin_partida(codigo: str) -> str:
    return f"No hay ninguna partida «{codigo}» en el catálogo de esta carpeta de trabajo."


def exigir_codigo(sesion: Session, lado: str, codigo: str) -> str:
    """`codigo` sin blancos en los bordes si es un insumo de la carpeta (compra) o una partida de
    su catálogo (cobro); si no, `NoExiste`."""
    _exigir_lado(lado)
    codigo = codigo.strip()
    if lado == "compra":
        condicion = exists().where(models.Insumo.codigo == codigo)
        mensaje = f"No hay ningún insumo «{codigo}» en esta carpeta de trabajo."
    else:
        condicion = exists().where(models.Partida.codigo == codigo)
        mensaje = _sin_partida(codigo)
    if not sesion.scalar(select(condicion)):
        raise NoExiste(mensaje)
    return codigo


# --- registrar y anular -----------------------------------------------------------------------


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
    `codigo` es un insumo de la carpeta (compra) o una partida de su catálogo (cobro): si no,
    `NoExiste`. La fecha no puede ser posterior a `ahora`. `ValueError` con el mensaje para la
    persona en lo demás. No confirma."""
    _exigir_lado(lado)
    if fuente_tipo not in FUENTES:
        raise ValueError(
            f"fuente_tipo {fuente_tipo!r}; se espera proveedor, competidor, cotizacion, maprex o "
            "compra"
        )
    responsable = _responsable(responsable)
    fuente = _texto_acotado(fuente, _LARGO_FUENTE, "fuente")
    if not fuente:
        raise ReglaDeMercado("Escriba de dónde sale el precio (la fuente).")
    nota = _texto_acotado(nota, _LARGO_NOTA, "nota")
    valor = _precio_positivo(precio)
    if fecha > ahora.date():
        raise ReglaDeMercado("La fecha de la observación no puede ser posterior a hoy.")
    moneda = _exigir_moneda(sesion, ahora.date())
    codigo = exigir_codigo(sesion, lado, codigo)
    fila = ObservacionDeMercado(
        lado=lado,
        codigo=codigo,
        fuente_tipo=fuente_tipo,
        fuente=fuente,
        fecha=fecha,
        moneda=moneda,
        precio=valor,
        nota=nota,
        responsable=responsable,
        fecha_hora=ahora,
        anulada_por=None,
    )
    sesion.add(fila)
    sesion.flush()
    return fila.id


def anular_observacion(
    sesion: Session, observacion_id: int, *, responsable: str, ahora: datetime
) -> int:
    """Anula la observación con un contraasiento y devuelve el `id` del contraasiento.

    `NoExiste` si no hay tal observación; `ObservacionAnulada` si ya está anulada o es un
    contraasiento. No confirma."""
    responsable = _responsable(responsable)
    original = sesion.get(ObservacionDeMercado, observacion_id)
    if original is None:
        raise NoExiste(
            f"No hay ninguna observación n.º {observacion_id} en esta carpeta de trabajo."
        )
    if original.anulada_por is not None:
        raise ObservacionAnulada(f"La observación n.º {observacion_id} ya está anulada.")
    contra = ObservacionDeMercado(
        lado=original.lado,
        codigo=original.codigo,
        fuente_tipo=original.fuente_tipo,
        fuente=original.fuente,
        fecha=original.fecha,
        moneda=original.moneda,
        precio=original.precio,
        nota=f"Anula la observación n.º {original.id}.",
        responsable=responsable,
        fecha_hora=ahora,
        anulada_por=None,
    )
    sesion.add(contra)
    sesion.flush()
    contra.anulada_por = contra.id
    original.anulada_por = contra.id
    sesion.flush()
    return contra.id


# --- estadísticas -----------------------------------------------------------------------------


def _cuartil_inc(ordenados: list[Decimal], p: Decimal) -> Decimal:
    """`CUARTIL.INC` de Excel: interpolación lineal en la posición `(n − 1)·p` (desde 0)."""
    posicion = (len(ordenados) - 1) * p
    abajo = int(posicion)  # posición >= 0: truncar es el piso
    fraccion = posicion - abajo
    if fraccion == 0:
        return ordenados[abajo]
    return ordenados[abajo] + fraccion * (ordenados[abajo + 1] - ordenados[abajo])


def observaciones_vigentes(
    sesion: Session, *, lado: str, codigo: str, hoy: date, dias: int = DIAS_POR_OMISION
) -> list[ObservacionDeMercado]:
    """Las observaciones no anuladas de `codigo` con fecha entre `hoy − dias` y `hoy`, en todas
    las monedas (las de otra moneda se ven pero no cuentan), por `id`."""
    _exigir_lado(lado)
    if dias < 0:
        raise ValueError(f"dias {dias}; se espera 0 o más")
    return list(
        sesion.scalars(
            select(ObservacionDeMercado)
            .where(
                ObservacionDeMercado.lado == lado,
                ObservacionDeMercado.codigo == codigo,
                ObservacionDeMercado.anulada_por.is_(None),
                ObservacionDeMercado.fecha >= hoy - timedelta(days=dias),
                ObservacionDeMercado.fecha <= hoy,
            )
            .order_by(ObservacionDeMercado.id)
        )
    )


@dataclass(frozen=True)
class ObservacionLeida:
    """Una observación vigente vista en la moneda de la carpeta: la fila tal como se guardó, y si
    estaba en otra moneda, su `equivalencia` (con la tasa del BCV de su día) o, si no hay tasa de
    ese día, `sin_tasa` con el texto que ve la persona. Nada se escribe."""

    fila: ObservacionDeMercado
    equivalencia: Equivalencia | None
    sin_tasa: str | None

    @property
    def cuenta(self) -> bool:
        """Entra en las cifras: está en la moneda de la carpeta o se pudo convertir."""
        return self.sin_tasa is None

    @property
    def valor(self) -> Decimal:
        """El precio en la moneda de la carpeta (exacto): el original o el convertido."""
        return self.fila.precio if self.equivalencia is None else self.equivalencia.convertido


def _leer(sesion: Session, fila: ObservacionDeMercado, moneda: str) -> ObservacionLeida:
    if fila.moneda == moneda:
        return ObservacionLeida(fila, None, None)
    try:
        equivalencia = equivalencia_del_dia(sesion, fila.precio, fila.moneda, moneda, fila.fecha)
    except SinTasaDelDia:
        return ObservacionLeida(fila, None, f"sin tasa del BCV del {fila.fecha:%d/%m/%Y}")
    return ObservacionLeida(fila, equivalencia, None)


def observaciones_leidas(
    sesion: Session, lado: str, codigo: str, hoy: date, dias: int = DIAS_POR_OMISION
) -> list[ObservacionLeida]:
    """Las observaciones vigentes de `codigo` (`observaciones_vigentes`) en la moneda de la
    carpeta: las de otra moneda, convertidas con la tasa del BCV del mismo día (Tarea D3)."""
    moneda = _exigir_moneda(sesion, hoy)
    filas = observaciones_vigentes(sesion, lado=lado, codigo=codigo, hoy=hoy, dias=dias)
    return [_leer(sesion, fila, moneda) for fila in filas]


def estadisticas(
    sesion: Session, *, lado: str, codigo: str, hoy: date, dias: int = DIAS_POR_OMISION
) -> Estadisticas:
    """n, mínimo, primer cuartil, mediana, promedio y máximo de las observaciones vigentes (no
    anuladas) de `codigo`, con fecha entre `hoy − dias` y `hoy`, en la moneda de la carpeta: las de
    otra moneda entran convertidas con la tasa del BCV de su día, y las que no la tienen quedan
    fuera y se cuentan aparte (`sin_tasa`)."""
    _exigir_lado(lado)
    if dias < 0:
        raise ValueError(f"dias {dias}; se espera 0 o más")
    moneda = _exigir_moneda(sesion, hoy)
    leidas = observaciones_leidas(sesion, lado, codigo, hoy, dias)
    cuentan = [o for o in leidas if o.cuenta]
    convertidas = sum(1 for o in cuentan if o.equivalencia is not None)
    sin_tasa = len(leidas) - len(cuentan)
    ids = tuple(o.fila.id for o in cuentan)
    if not cuentan:
        return Estadisticas(moneda, 0, None, None, None, None, None, ids, 0, sin_tasa, dias)
    precios = sorted(o.valor for o in cuentan)
    return Estadisticas(
        moneda=moneda,
        n=len(precios),
        minimo=precios[0],
        q1=_cuartil_inc(precios, _Q1),
        mediana=_cuartil_inc(precios, _MEDIANA),
        promedio=sum(precios, Decimal(0)) / len(precios),
        maximo=precios[-1],
        ids=ids,
        convertidas=convertidas,
        sin_tasa=sin_tasa,
        dias=dias,
    )


# --- piso ---------------------------------------------------------------------------------------


def _parametros(sesion: Session, proyecto: str | None, moneda: str) -> ParametrosCosto:
    """Los de la versión vigente de la obra (`parametros_de_version`, los mismos de la Hoja); sin
    obra o sin versión, los por omisión.

    El bono de alimentación es un monto en la moneda de la versión: si la obra está en otra moneda
    que la carpeta, no se mezcla y se usa el de omisión (los factores sí valen)."""
    if proyecto is None:
        return ParametrosCosto()
    existe = sesion.scalar(select(exists().where(models.Proyecto.nombre == proyecto)))
    if not existe:
        raise NoExiste(f"No hay ninguna obra «{proyecto}» en esta carpeta de trabajo.")
    vigente = version_vigente(sesion, proyecto)
    if vigente is None:
        return ParametrosCosto()
    parametros = parametros_de_version(vigente)
    if vigente.moneda != moneda:
        parametros = replace(parametros, bono_alimentacion=ParametrosCosto().bono_alimentacion)
    return parametros


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
    IVA). `SinListaParaArmar` sin lista en la moneda de la carpeta; `NoExiste` si la obra o la
    partida no existen; `CatalogoIncompleto` si a la partida le falta un precio o su rendimiento."""
    lista = lista_para_armar(sesion, fecha)
    parametros = _parametros(sesion, proyecto, lista.moneda)
    try:
        composicion = catalogo.composicion(codigo_partida, fecha=fecha, lista=lista)
    except KeyError:
        raise NoExiste(_sin_partida(codigo_partida)) from None
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
        return Propuesta(precio=max(mostrado, minimo_sin_perder), razon=RAZON_POR_ENCIMA, piso=piso)
    return Propuesta(precio=minimo_sin_perder, razon=RAZON_POR_DEBAJO, piso=piso)


def margen(objetivo: Decimal, precio_unitario: Decimal) -> Decimal:
    """(objetivo − precio unitario) / precio unitario, en porcentaje con una cifra decimal
    (`ROUND_HALF_UP`): negativo si el objetivo queda por debajo del precio con utilidad."""
    if precio_unitario <= 0:
        raise ValueError("el precio unitario debe ser mayor que cero")
    porcentaje = (objetivo - precio_unitario) / precio_unitario * _CIEN
    return porcentaje.quantize(_DECIMA, rounding=ROUND_HALF_UP)


# --- usar un precio -----------------------------------------------------------------------------


def _citada(
    sesion: Session, observacion_id: int, lado: str, codigo: str, moneda: str
) -> ObservacionDeMercado:
    """La observación citada si es vigente (no anulada), de ese lado y de ese código y entra en las
    cifras en `moneda` (la de la carpeta): está en esa moneda o se convierte con la tasa del BCV de
    su día (Tarea D3); si no, `ReglaDeMercado`. No se exige que esté en la ventana de 90 días:
    la persona puede ampliarla al estudiar, y una observación vieja no anulada sigue siendo
    cierta."""
    fila = sesion.get(ObservacionDeMercado, observacion_id)
    if fila is None or fila.anulada_por is not None or (fila.lado, fila.codigo) != (lado, codigo):
        raise ReglaDeMercado(MENSAJE_OBSERVACION_AJENA)
    leida = _leer(sesion, fila, moneda)
    if not leida.cuenta:
        raise ReglaDeMercado(
            f"La observación elegida está en {fila.moneda} y no hay tasa del BCV del "
            f"{fila.fecha:%d/%m/%Y} para convertirla a {moneda}."
        )
    return fila


def apus_afectados(sesion: Session, codigo_insumo: str) -> list[str]:
    """Las partidas del catálogo cuya composición usa el insumo, ordenadas por código: las que
    cambian de precio si cambia el suyo en la lista para armar. `NoExiste` sin tal insumo."""
    codigo = exigir_codigo(sesion, "compra", codigo_insumo)
    return list(
        sesion.scalars(
            select(models.Partida.codigo)
            .join(models.ComposicionAPU, models.ComposicionAPU.partida_id == models.Partida.id)
            .join(models.Insumo, models.Insumo.id == models.ComposicionAPU.insumo_id)
            .where(models.Insumo.codigo == codigo)
            .distinct()
            .order_by(models.Partida.codigo)
        )
    )


def usar_precio_de_compra(
    sesion: Session,
    codigo_insumo: str,
    precio: str,
    *,
    observacion_id: int | None,
    fecha: date,
    responsable: str,
) -> models.ListaPrecios:
    """Pone `precio` (tecleado) como el del insumo en la lista de hoy de la carpeta y la devuelve.

    La lista es `lista_de_hoy(sesion, fecha, nueva_si_usada=True)`: si la de hoy ya la usa una
    versión guardada, se deriva otra del mismo día; las listas viejas y las versiones no cambian.
    El origen del precio dice «Estudio de mercado: observación n.º {id}, por {responsable}» (o sin
    la observación). Todo se valida antes de escribir: `CifraInvalida`, precio no positivo,
    `NoExiste`, una observación que no es un precio de compra vigente de ese insumo en la moneda
    de la carpeta (`ReglaDeMercado`), `SinListaParaArmar`. No confirma."""
    responsable = _responsable(responsable)
    valor = _precio_positivo(precio)
    codigo = exigir_codigo(sesion, "compra", codigo_insumo)
    fuente = FUENTE_DEL_PRECIO
    if observacion_id is not None:
        citada = _citada(sesion, observacion_id, "compra", codigo, _exigir_moneda(sesion, fecha))
        fuente = f"{FUENTE_DEL_PRECIO}: observación n.º {citada.id}"
    lista = lista_de_hoy(sesion, fecha, nueva_si_usada=True)
    insumo = sesion.scalars(select(models.Insumo).where(models.Insumo.codigo == codigo)).one()
    fila = sesion.scalars(
        select(models.PrecioInsumo).where(
            models.PrecioInsumo.lista_id == lista.id,
            models.PrecioInsumo.insumo_id == insumo.id,
        )
    ).one_or_none()
    if fila is None:
        fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=valor)
        sesion.add(fila)
    else:
        fila.precio = valor
    sesion.flush()
    origen = sesion.get(models.PrecioOrigen, fila.id)
    if origen is None:
        origen = models.PrecioOrigen(precio_id=fila.id)
        sesion.add(origen)
    origen.moneda_original = lista.moneda
    origen.precio_original = valor
    origen.fecha_precio = fecha
    origen.tasa = None
    origen.fecha_tasa = None
    origen.fuente_tasa = ""
    origen.fuente = f"{fuente}, por {responsable}"
    sesion.flush()
    return lista


def usar_precio_de_cobro(
    sesion: Session,
    codigo_partida: str,
    precio: str,
    *,
    observaciones: Sequence[int],
    responsable: str,
    ahora: datetime,
) -> PrecioObjetivo:
    """Guarda `precio` (tecleado) como el precio de venta objetivo de la partida, en la moneda de
    la carpeta, citando las observaciones de cobro de las que sale (sin repetir, en orden). Vale
    el último por partida. `CifraInvalida`; `ReglaDeMercado` con un precio no positivo o de más de
    2 decimales (un precio de venta va en céntimos) o una observación que no es un precio de cobro
    vigente de esa partida en la moneda de la carpeta; `NoExiste`; `CarpetaSinMoneda`. No
    confirma."""
    responsable = _responsable(responsable)
    valor = _precio_positivo(precio)
    if valor != valor.quantize(_CENTIMO):
        raise ReglaDeMercado("El precio objetivo admite hasta 2 decimales (céntimos).")
    codigo = exigir_codigo(sesion, "cobro", codigo_partida)
    moneda = _exigir_moneda(sesion, ahora.date())
    citas = sorted(set(observaciones))
    for ident in citas:
        _citada(sesion, ident, "cobro", codigo, moneda)
    texto = json.dumps(citas, separators=(",", ":"))
    if len(texto) > _LARGO_CITAS:
        raise ReglaDeMercado("Son demasiadas observaciones para citar: elija menos.")
    fila = PrecioObjetivo(
        codigo_partida=codigo,
        precio=valor,
        moneda=moneda,
        observaciones=texto,
        responsable=responsable,
        fecha_hora=ahora,
    )
    sesion.add(fila)
    sesion.flush()
    return fila


def objetivos(sesion: Session, codigos: Sequence[str]) -> list[PrecioObjetivo]:
    """El último precio objetivo de cada partida de `codigos` que tenga uno, en el orden pedido
    (sin repetir)."""
    pedidos = list(dict.fromkeys(codigos))
    if not pedidos:
        return []
    ultimos = (
        select(func.max(PrecioObjetivo.id))
        .where(PrecioObjetivo.codigo_partida.in_(pedidos))
        .group_by(PrecioObjetivo.codigo_partida)
    )
    filas = {
        fila.codigo_partida: fila
        for fila in sesion.scalars(select(PrecioObjetivo).where(PrecioObjetivo.id.in_(ultimos)))
    }
    return [filas[codigo] for codigo in pedidos if codigo in filas]


# --- pendientes de la mesa ----------------------------------------------------------------------


def pendientes_de_mercado(sesion: Session, hoy: date) -> list[Pendiente]:
    """Fuente «precios» de la mesa: por obra, las partidas de su versión vigente cuyo primer
    cuartil de cobro de los últimos 90 días es menor que su piso (con los parámetros de esa
    versión) → «{código}: el mercado cobra menos que su costo». Sin moneda o sin lista para armar
    no dice nada; una partida cuyo costo no se puede calcular se salta."""
    # `aplicacion.mesa` registra esta fuente en `FUENTES`: importarla arriba sería circular.
    from aplicacion.mesa import Pendiente, Siguiente

    try:
        lista_para_armar(sesion, hoy)
        _exigir_moneda(sesion, hoy)
    except (SinListaParaArmar, CarpetaSinMoneda):
        return []
    catalogo = Catalogo(sesion)
    accion = Siguiente("Estudio de mercado", "mercado")
    cuartiles: dict[str, Decimal | None] = {}
    salida = []
    for fila in proyectos_del_caso(sesion):
        if fila.version_id is None:
            continue
        version = sesion.get(models.Presupuesto, fila.version_id)
        assert version is not None
        for codigo in dict.fromkeys(p.partida.codigo for p in version.partidas):
            if codigo not in cuartiles:
                cuartiles[codigo] = estadisticas(sesion, lado="cobro", codigo=codigo, hoy=hoy).q1
            q1 = cuartiles[codigo]
            if q1 is None:
                continue
            try:
                piso, _ = piso_de_cobro(sesion, catalogo, codigo, proyecto=fila.nombre, fecha=hoy)
            except (ValueError, CatalogoIncompleto):
                continue
            if q1 < piso:
                texto = f"{codigo}: el mercado cobra menos que su costo"
                salida.append(Pendiente(str(fila.id), fila.nombre, texto, accion))
    return salida
