"""RF-100 (deseable, S3-6): variaciones atípicas en la serie de precios de un insumo, sin Streamlit.

Arma la serie fechada de un insumo desde las listas del caso (las de la empresa de S1, las MaPreX
y las globales; las listas de **proyecto**, que nacen de una cotización, no entran), con la
moneda, la fecha y la tasa de cada precio (`origenes_efectivos`: el `PrecioOrigen` si existe y, si
no, la lista y su tasa), y se la pasa a `ml.anomaly.series.analizar`. Cada variación atípica es un
hallazgo `ATIPICO` de severidad **ADVERTENCIA**, nunca ERROR: apoya a quien revisa, no mide (la
tesis lo presenta así). No guarda nada y no bloquea guardar, exportar ni firmar: solo las dos
pantallas de precios importan este módulo; ni el informe de verificación ni la entrega lo conocen.
Sin el extra `ml` devuelve `None` (sin hallazgo ni traza). `ml/` no conoce la base: aquí se arman
los puntos y allí se juzgan.

Un precio que una lista de empresa **hereda** de su base (el mismo insumo con la misma moneda,
precio, fecha y fuente originales, como en `core.catalog.empresa.es_heredado`) es la misma
observación que la de la base, no otra, y no entra de nuevo: si no, la serie tendría variaciones
de 0 que no ocurrieron. Dos listas **independientes** con el mismo precio y la misma fecha son dos
observaciones.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from types import ModuleType

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.presupuesto import CODIGO_ATIPICO
from core.catalog.origen import OrigenEfectivo, origenes_efectivos
from core.contracts.verificacion import Hallazgo, Severidad
from ui.texto_seguro import texto_seguro

__all__ = [
    "AVISO_SIN_ML",
    "MENSAJE_NADA_ATIPICO",
    "ROTULO_BOTON",
    "BusquedaAtipicos",
    "atipicos_de_insumos",
    "atipicos_del_insumo",
    "avisos",
    "codigos_de_la_lista",
    "hallazgos_de_la_serie",
    "puntos_del_insumo",
]

DOS_DECIMALES = Decimal("0.01")
#: Lo que una lista de empresa conserva de su base cuando hereda un precio (`_CAMPOS_DE_HERENCIA`
#: de `core.catalog.empresa`; la tasa puede diferir si la base se convirtió).
_CAMPOS_DE_HERENCIA = ("moneda_original", "precio_original", "fecha_precio", "fuente")

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


@dataclass(frozen=True, slots=True)
class BusquedaAtipicos:
    """Lo que devuelve la búsqueda de varios insumos: sus hallazgos y los orígenes (listas) de los
    precios en Bs a los que les faltó la tasa y por eso se omitieron, sin repetir. `no_analizados`
    son los insumos que no se pudieron analizar, `(código, motivo)`, p. ej. por una moneda que no es
    Bs ni USD en su lista: un insumo así no impide analizar los demás."""

    hallazgos: tuple[Hallazgo, ...]
    sin_tasa: tuple[str, ...]
    no_analizados: tuple[tuple[str, str], ...] = ()


def _cargar_series() -> ModuleType:
    import ml.anomaly.series

    return ml.anomaly.series


def _es_heredado(o: OrigenEfectivo, de_base: OrigenEfectivo | None) -> bool:
    return de_base is not None and all(
        getattr(o, campo) == getattr(de_base, campo) for campo in _CAMPOS_DE_HERENCIA
    )


def puntos_del_insumo(
    session: Session,
    codigo: str,
    series: ModuleType | None = None,
    origenes: dict[int, dict[int, OrigenEfectivo]] | None = None,
) -> list:
    """Los `PuntoDePrecio` del insumo `codigo`, uno por observación de cada lista que no es de
    proyecto, por fecha del precio y nombre de la lista.

    La moneda, la fecha y la tasa de cada punto son las de su `OrigenEfectivo`: manda el precio
    sobre la lista (S1 §5.1). `origenes` (`{lista_id: origenes_efectivos(lista)}`) se puede
    compartir entre insumos para leer cada lista una sola vez; se completa aquí."""
    series = series or _cargar_series()
    origenes = {} if origenes is None else origenes
    filas = session.execute(
        select(models.PrecioInsumo.id, models.ListaPrecios, models.ListaEmpresa.lista_base_id)
        .join(models.Insumo, models.Insumo.id == models.PrecioInsumo.insumo_id)
        .join(models.ListaPrecios, models.ListaPrecios.id == models.PrecioInsumo.lista_id)
        .outerjoin(
            models.ListaPreciosOrigen, models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id
        )
        .outerjoin(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.ListaPrecios.id)
        .where(models.Insumo.codigo == codigo)
        .where(
            models.ListaPreciosOrigen.alcance.is_(None)
            | (models.ListaPreciosOrigen.alcance != models.ALCANCE_PROYECTO)
        )
        .order_by(models.ListaPrecios.fecha_vigencia, models.ListaPrecios.id)
    ).all()
    del_insumo: dict[int, OrigenEfectivo] = {}  # lista_id -> origen del precio de este insumo
    for precio_id, lista, _ in filas:
        if lista.id not in origenes:
            origenes[lista.id] = origenes_efectivos(session, lista)
        del_insumo[lista.id] = origenes[lista.id][precio_id]
    puntos = []
    for _, lista, base_id in filas:
        o = del_insumo[lista.id]
        if base_id is not None and _es_heredado(o, del_insumo.get(base_id)):
            continue  # lo heredado de la base es la misma observación que la de la base
        puntos.append(
            series.PuntoDePrecio(
                o.fecha_precio, o.precio_original, o.moneda_original, o.tasa, lista.nombre
            )
        )
    return puntos


def hallazgos_de_la_serie(
    codigo: str, resultado, series: ModuleType | None = None
) -> list[Hallazgo]:
    """Un hallazgo ADVERTENCIA por variación atípica, con su monto en porcentaje. `series` es el
    módulo que entregó `cargar_series` (de él sale `tramo`)."""
    tramo = (series or _cargar_series()).tramo
    hallazgos = []
    for atipica in resultado.atipicas:
        porcentaje = format((atipica.valor * 100).quantize(DOS_DECIMALES), "f")
        antes, despues = tramo(atipica.id)
        hallazgos.append(
            Hallazgo(
                regla=CODIGO_ATIPICO,
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{codigo}: variación de {porcentaje} % entre {antes.isoformat()} y "
                    f"{despues.isoformat()} (en USD) se aparta del historial de variaciones "
                    "del insumo"
                ),
                origen_ids=(f"{codigo}|{atipica.id}",),
                valor_observado=atipica.valor,
            )
        )
    return hallazgos


def atipicos_de_insumos(
    session: Session,
    codigos: Iterable[str],
    cargar_series: Callable[[], ModuleType] = _cargar_series,
) -> BusquedaAtipicos | None:
    """La búsqueda de RF-100 sobre varios insumos, o `None` si el extra `ml` no está instalado.
    Lee los orígenes de cada lista una sola vez para todos (costo O(listas × precios + puntos)) y
    junta los hallazgos y las listas en Bs sin tasa que se omitieron. Solo lee."""
    hallazgos: list[Hallazgo] = []
    sin_tasa: list[str] = []
    no_analizados: list[tuple[str, str]] = []
    origenes: dict[int, dict[int, OrigenEfectivo]] = {}
    try:
        series = cargar_series()
        for codigo in codigos:
            try:
                resultado = series.analizar(puntos_del_insumo(session, codigo, series, origenes))
            except ValueError as error:  # una moneda que no es Bs ni USD: se dice y se sigue
                no_analizados.append((codigo, str(error)))
                continue
            hallazgos.extend(hallazgos_de_la_serie(codigo, resultado, series))
            sin_tasa.extend(o for o in resultado.serie.sin_tasa if o not in sin_tasa)
    except ImportError:  # `scikit-learn` llega tarde: al ajustar el bosque
        return None
    return BusquedaAtipicos(tuple(hallazgos), tuple(sin_tasa), tuple(no_analizados))


def atipicos_del_insumo(
    session: Session, codigo: str, cargar_series: Callable[[], ModuleType] = _cargar_series
) -> list[Hallazgo] | None:
    """Los hallazgos de RF-100 del insumo, o `None` si el extra `ml` no está instalado.
    Una lista vacía es «nada atípico» o «serie corta» (el detector se abstiene). Solo lee."""
    busqueda = atipicos_de_insumos(session, [codigo], cargar_series)
    return None if busqueda is None else list(busqueda.hallazgos)


def avisos(busqueda: BusquedaAtipicos | None) -> list[tuple[str, str]]:
    """Lo que las pantallas muestran de una búsqueda, como `(nivel, texto)` con el nivel de
    Streamlit (`info`, `success` o `warning`) y el texto ya escapado (RV-14). Nunca `error`."""
    if busqueda is None:
        return [("info", AVISO_SIN_ML)]
    salida = [
        ("info", f"Precio en Bs sin tasa, omitido: {texto_seguro(lista)}")
        for lista in busqueda.sin_tasa
    ]
    salida += [
        ("info", f"{texto_seguro(codigo)}: no se pudo analizar ({texto_seguro(motivo)})")
        for codigo, motivo in busqueda.no_analizados
    ]
    if not busqueda.hallazgos:
        salida.append(("success", MENSAJE_NADA_ATIPICO))
    salida += [("warning", texto_seguro(h.descripcion)) for h in busqueda.hallazgos]
    return salida


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
