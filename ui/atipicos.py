"""RF-100 (deseable, S3-6): variaciones atípicas en la serie de precios de un insumo, sin Streamlit.

Arma la serie fechada de un insumo desde las listas del caso (las de la empresa de S1, las MaPreX
y las globales; las listas de **proyecto**, que nacen de una cotización, no entran), con la
moneda, la fecha y la tasa de cada precio (`origenes_efectivos`: el `PrecioOrigen` si existe y, si
no, la lista y su tasa), y se la pasa a `ml.anomaly.series.analizar`. Cada variación atípica es un
hallazgo `ATIPICO` de severidad **ADVERTENCIA**, nunca ERROR: apoya a quien revisa, no mide (la
tesis lo presenta así). No guarda nada y no bloquea guardar, exportar ni firmar. Sin el extra `ml`
devuelve `None` (sin hallazgo ni traza). `ml/` no conoce la base: aquí se arman los puntos y allí
se juzgan.

Un precio que una lista de empresa **hereda** de su base conserva el mismo origen (moneda, precio y
fecha originales): es la misma observación, no otra, y entra una sola vez; si no, la serie
tendría variaciones de 0 que no ocurrieron.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from types import ModuleType

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.presupuesto import CODIGO_ATIPICO
from core.catalog.origen import origenes_efectivos
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = [
    "AVISO_SIN_ML",
    "MENSAJE_NADA_ATIPICO",
    "ROTULO_BOTON",
    "atipicos_del_insumo",
    "codigos_de_la_lista",
    "hallazgos_de_la_serie",
    "puntos_del_insumo",
]

DOS_DECIMALES = Decimal("0.01")

#: Los textos que comparten las dos pantallas donde vive el botón (pestaña Precios y lista de la
#: empresa); aquí para no repetirlos y para que ninguna pintura dependa de Streamlit.
ROTULO_BOTON = "Buscar variaciones atípicas de precio"
AVISO_SIN_ML = (
    "La búsqueda de variaciones atípicas necesita el extra `ml` (scikit-learn), que no está "
    "instalado en este equipo. No se buscó nada y nada se bloquea."
)
MENSAJE_NADA_ATIPICO = (
    "Ninguna variación atípica de precio (una serie de menos de 8 variaciones no se juzga)."
)


def _cargar_series() -> ModuleType:
    import ml.anomaly.series

    return ml.anomaly.series


def puntos_del_insumo(session: Session, codigo: str, series: ModuleType | None = None) -> list:
    """Los `PuntoDePrecio` del insumo `codigo`, uno por observación de cada lista que no es de
    proyecto, por fecha del precio y nombre de la lista.

    La moneda, la fecha y la tasa de cada punto son las de su `OrigenEfectivo`: manda el precio
    sobre la lista (S1 §5.1)."""
    series = series or _cargar_series()
    filas = session.execute(
        select(models.PrecioInsumo.id, models.ListaPrecios)
        .join(models.Insumo, models.Insumo.id == models.PrecioInsumo.insumo_id)
        .join(models.ListaPrecios, models.ListaPrecios.id == models.PrecioInsumo.lista_id)
        .outerjoin(
            models.ListaPreciosOrigen, models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id
        )
        .where(models.Insumo.codigo == codigo)
        .where(
            models.ListaPreciosOrigen.alcance.is_(None)
            | (models.ListaPreciosOrigen.alcance != models.ALCANCE_PROYECTO)
        )
        .order_by(models.ListaPrecios.fecha_vigencia, models.ListaPrecios.id)
    ).all()
    origenes: dict[int, dict] = {}  # por lista: una sola lectura de sus orígenes
    puntos = []
    vistos: set[tuple] = set()
    for precio_id, lista in filas:
        if lista.id not in origenes:
            origenes[lista.id] = origenes_efectivos(session, lista)
        o = origenes[lista.id][precio_id]
        observacion = (o.fecha_precio, o.moneda_original, o.precio_original)
        if observacion in vistos:  # lo heredado de la base es la misma observación
            continue
        vistos.add(observacion)
        puntos.append(
            series.PuntoDePrecio(
                o.fecha_precio, o.precio_original, o.moneda_original, o.tasa, lista.nombre
            )
        )
    return puntos


def hallazgos_de_la_serie(codigo: str, resultado) -> list[Hallazgo]:
    """Un hallazgo ADVERTENCIA por variación atípica, con su monto en porcentaje."""
    hallazgos = []
    for atipica in resultado.atipicas:
        porcentaje = format((atipica.valor * 100).quantize(DOS_DECIMALES), "f")
        antes, despues = atipica.id.split("#")[0].split(">")
        hallazgos.append(
            Hallazgo(
                regla=CODIGO_ATIPICO,
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{codigo}: variación de {porcentaje} % entre {antes} y {despues} "
                    "(en USD) se aparta del historial de variaciones del insumo"
                ),
                origen_ids=(f"{codigo}|{atipica.id}",),
                valor_observado=atipica.valor,
            )
        )
    return hallazgos


def atipicos_del_insumo(
    session: Session, codigo: str, cargar_series: Callable[[], ModuleType] = _cargar_series
) -> list[Hallazgo] | None:
    """Los hallazgos de RF-100 del insumo, o `None` si el extra `ml` no está instalado.
    Una lista vacía es «nada atípico» o «serie corta» (el detector se abstiene). Solo lee."""
    try:
        series = cargar_series()
        resultado = series.analizar(puntos_del_insumo(session, codigo, series))
    except ImportError:  # `scikit-learn` llega tarde: al ajustar el bosque
        return None
    return hallazgos_de_la_serie(codigo, resultado)


def codigos_de_la_lista(session: Session, lista_id: int) -> list[str]:
    """Los códigos de los insumos que valora la lista, en orden (los que revisa su botón)."""
    return list(
        session.scalars(
            select(models.Insumo.codigo)
            .join(models.PrecioInsumo, models.PrecioInsumo.insumo_id == models.Insumo.id)
            .where(models.PrecioInsumo.lista_id == lista_id)
            .order_by(models.Insumo.codigo)
        )
    )
