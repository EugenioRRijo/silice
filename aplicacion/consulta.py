"""Autocompletado con tablas venezolanas (plan vial, Tarea 20).

Una sola función, `buscar(sesion, tabla, q)`, para los campos de la interfaz que piden un dato
que ya existe en una tabla: la partida vial, el insumo, la tasa del BCV de un día, el oficio de la
mano de obra. Cada `Sugerencia` trae el `valor` que se guarda, la `etiqueta` que se lee y la
`fuente` de la que sale, para que nadie elija un dato sin saber de dónde viene.

La regla de búsqueda es la de `aplicacion.busqueda` (sin distinguir mayúsculas ni acentos, todas las
palabras en cualquier orden, el código exacto primero); aquí solo cambian las filas.

Tablas:

- `partidas_viales`: las partidas de `adapters.vial.constantes.PARTIDAS_VIALES`.
- `insumos`: materiales y equipos del catálogo de la carpeta de trabajo.
- `salarios_cct`: la mano de obra del catálogo (los oficios con su jornal, que es lo que el
  tabulador de la convención colectiva fija). El texto de la convención no está cargado como tabla
  en el repositorio: lo que se ofrece es el oficio del catálogo, no un salario propio.
- `tasa_bcv`: las tasas de venta importadas (serie `BCV-USD-VENTA`), la más reciente primero. El
  `valor` es la fecha en ISO; se busca por esa fecha, por `dd/mm/aaaa` o por el monto.

Detalle y precio para armar (AC1b, Componer): en `insumos` y `salarios_cct`, con `detalle` cada
sugerencia trae además la `descripcion` y la `unidad` del insumo; con `para_armar_al` (que implica
el detalle), el `precio` de la lista con que se arma a esa fecha, con su `moneda` y la
`fecha_precio` desde la que rige. Esa lista es la de `listas_para_armar.lista_para_armar`, la misma
con que Componer guarda, y no la vigente de hoy en cualquier moneda. Si la vigente a esa fecha está
en otra moneda que la de la carpeta no viaja ningún precio: solo su moneda, su fecha y el
`aviso_precio` («El catálogo lo tiene en USD; escriba el precio en Bs.»). Sin lista no hay precio.
Sin `detalle` ni `para_armar_al` la sugerencia es la de siempre; las otras dos tablas no cambian.

Lo ya usado en la carpeta (AC4, pedido de Eugenio del 2026-10-21), para guiar dos campos de texto
que siguen admitiendo un valor propio. Son listas cortas que la interfaz pide una vez y filtra:

- `unidades_usadas`: las unidades de las partidas y los insumos del catálogo, agrupadas con la única
  tabla de alias del sistema (`core.contracts.unidades.normalizar_unidad`; no hay otra lista de
  unidades en el núcleo): «m3», «m³» y «M3» son una sola, `m3`, con sus grafías y cuántas filas la
  usan. Las más usadas primero; a igual uso, por orden alfabético. Una unidad desconocida queda en
  minúsculas y sin traducir, como la deja el núcleo.
- `proveedores_usados`: los proveedores de las cotizaciones **activas** de la carpeta (diseño §13),
  sin repetir (sin distinguir mayúsculas, acentos ni espacios), escritos como en su cotización más
  reciente y con la fecha de esa cotización; el último usado primero. Activa es la que está en la
  lista de precios de la versión vigente de alguna obra (la de mayor id no descartada, el mismo
  criterio que `core.budget.edicion.version_vigente`): retirar una cotización crea una versión
  nueva sobre una lista sin ella, así que la retirada queda solo en listas de versiones viejas; la
  de una versión descartada o la de una lista que ninguna versión usa tampoco cuentan.

Sin Streamlit ni FastAPI; solo lee.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from adapters.vial.constantes import PARTIDAS_VIALES
from aplicacion.busqueda import LARGO_MINIMO, rango
from aplicacion.listas_para_armar import (
    SinListaParaArmar,
    lista_para_armar,
    moneda_de_la_carpeta,
)
from core import models
from core.catalog import Catalogo, CatalogoIncompleto
from core.catalog.indices import SERIE_USD_VENTA, UNIDAD_TASA
from core.contracts.unidades import normalizar_unidad
from core.verification.texto import normalizar_texto

__all__ = [
    "TABLAS",
    "ProveedorUsado",
    "Sugerencia",
    "UnidadUsada",
    "buscar",
    "proveedores_usados",
    "unidades_usadas",
]

TABLAS = ("partidas_viales", "insumos", "tasa_bcv", "salarios_cct")

FUENTE_PARTIDAS = "Partidas viales de Sílice"
FUENTE_CATALOGO = "Catálogo de la carpeta de trabajo"
TIPOS_DE_INSUMO = ("material", "equipo")
TIPO_MANO_DE_OBRA = "mano_obra"


@dataclass(frozen=True)
class Sugerencia:
    """Una fila ofrecida: lo que se guarda, lo que se lee y de dónde sale.

    El resto solo lo llenan `detalle` y `para_armar_al` (insumos y salarios); `None` es «no viene».
    `precio` está en `moneda`, rige desde `fecha_precio` y nunca viaja en otra moneda que la de la
    carpeta: en ese caso va `aviso_precio` y el precio queda en `None`."""

    valor: str
    etiqueta: str
    fuente: str
    descripcion: str | None = None
    unidad: str | None = None
    precio: Decimal | None = None
    moneda: str | None = None
    fecha_precio: date | None = None
    aviso_precio: str | None = None


@dataclass(frozen=True)
class _PreciosParaArmar:
    """La lista vigente a la fecha de armar, sus precios por insumo y la moneda de la carpeta."""

    lista: models.ListaPrecios
    precios: dict[int, Decimal]
    moneda_de_trabajo: str

    @property
    def en_otra_moneda(self) -> bool:
        return self.lista.moneda != self.moneda_de_trabajo


def _con_coma(valor: Decimal) -> str:
    """`41.25` -> «41,25»: coma decimal y punto de miles (decisión de Eugenio del 25-10)."""
    entera, _, fraccion = format(valor, "f").partition(".")
    fraccion = fraccion.rstrip("0").ljust(2, "0")
    miles = f"{int(entera):,}".replace(",", ".")
    return f"{miles},{fraccion}"


def _ordenar(filas: list[tuple[int, str, str, Sugerencia]], limite: int) -> list[Sugerencia]:
    filas.sort(key=lambda fila: fila[:3])
    return [fila[3] for fila in filas[:limite]]


def _por_codigo_y_descripcion(
    filas: list[tuple[str, str, Sugerencia]], texto: str, limite: int
) -> list[Sugerencia]:
    halladas = []
    for codigo, descripcion, sugerencia in filas:
        orden = rango(codigo, descripcion, texto)
        if orden is not None:
            halladas.append((orden, normalizar_texto(descripcion), codigo, sugerencia))
    return _ordenar(halladas, limite)


def _partidas_viales(texto: str, limite: int) -> list[Sugerencia]:
    filas = [
        (
            codigo,
            descripcion,
            Sugerencia(codigo, f"{descripcion} ({codigo}, {unidad})", FUENTE_PARTIDAS),
        )
        for codigo, descripcion, unidad in PARTIDAS_VIALES.values()
    ]
    return _por_codigo_y_descripcion(filas, texto, limite)


def _precios_para_armar(sesion: Session, fecha: date) -> _PreciosParaArmar | None:
    """La lista con que se arma a `fecha` (`lista_para_armar`); si la vigente está en otra moneda
    que la de la carpeta, esa (para avisar, nunca para copiar); sin lista vigente, `None`."""
    try:
        lista = lista_para_armar(sesion, fecha)
    except SinListaParaArmar:
        try:
            lista = Catalogo(sesion).lista_vigente(fecha)
        except CatalogoIncompleto:
            return None
    moneda = moneda_de_la_carpeta(sesion, fecha) or lista.moneda
    precios = {precio.insumo_id: precio.precio for precio in lista.precios}
    return _PreciosParaArmar(lista, precios, moneda)


def _con_detalle(
    sugerencia: Sugerencia,
    insumo: models.Insumo,
    para_armar: _PreciosParaArmar | None,
) -> Sugerencia:
    """La sugerencia con su descripción y su unidad y, si la lista lo tiene, su precio o aviso."""
    con_detalle = replace(sugerencia, descripcion=insumo.descripcion, unidad=insumo.unidad or None)
    precio = None if para_armar is None else para_armar.precios.get(insumo.id)
    if para_armar is None or precio is None:
        return con_detalle
    lista = para_armar.lista
    if para_armar.en_otra_moneda:
        columna = "sueldo" if insumo.tipo == TIPO_MANO_DE_OBRA else "precio"
        aviso = (
            f"El catálogo lo tiene en {lista.moneda}; escriba el {columna} en "
            f"{para_armar.moneda_de_trabajo}."
        )
        return replace(
            con_detalle, moneda=lista.moneda, fecha_precio=lista.fecha_vigencia, aviso_precio=aviso
        )
    return replace(
        con_detalle, precio=precio, moneda=lista.moneda, fecha_precio=lista.fecha_vigencia
    )


def _insumos(
    sesion: Session,
    tipos: tuple[str, ...],
    texto: str,
    limite: int,
    *,
    detalle: bool = False,
    para_armar_al: date | None = None,
) -> list[Sugerencia]:
    filas = []
    insumos: dict[str, models.Insumo] = {}
    for insumo in sesion.scalars(select(models.Insumo).where(models.Insumo.tipo.in_(tipos))):
        unidad = f", {insumo.unidad}" if insumo.unidad else ""
        etiqueta = f"{insumo.descripcion} ({insumo.codigo}{unidad})"
        fuente = f"{FUENTE_CATALOGO}: {insumo.tipo.replace('_', ' ')}"
        insumos[insumo.codigo] = insumo
        filas.append(
            (insumo.codigo, insumo.descripcion, Sugerencia(insumo.codigo, etiqueta, fuente))
        )
    halladas = _por_codigo_y_descripcion(filas, texto, limite)
    if not detalle and para_armar_al is None:
        return halladas
    para_armar = None if para_armar_al is None else _precios_para_armar(sesion, para_armar_al)
    return [_con_detalle(s, insumos[s.valor], para_armar) for s in halladas]


def _tasas(sesion: Session, texto: str, limite: int) -> list[Sugerencia]:
    palabras = texto.split()
    consulta = (
        select(models.ValorIndice)
        .join(models.SerieIndice)
        .where(models.SerieIndice.codigo == SERIE_USD_VENTA)
        .order_by(models.ValorIndice.fecha.desc(), models.ValorIndice.importacion_id.desc())
    )
    vistas: set[str] = set()
    halladas: list[Sugerencia] = []
    for fila in sesion.scalars(consulta):
        iso = fila.fecha.isoformat()
        if iso in vistas:  # una revisión posterior de la misma fecha manda (como `tasa_aplicable`)
            continue
        vistas.add(iso)
        monto = _con_coma(fila.valor)
        pajar = normalizar_texto(f"{iso} {fila.fecha:%d/%m/%Y} {monto}")
        if all(palabra in pajar for palabra in palabras):
            provisional = " (provisional)" if fila.provisional else ""
            halladas.append(
                Sugerencia(
                    iso,
                    f"{fila.fecha:%d/%m/%Y}: {monto} {UNIDAD_TASA}{provisional}",
                    f"BCV, tasa de venta, importación n.º {fila.importacion_id}",
                )
            )
    return halladas[:limite]


def buscar(
    sesion: Session,
    tabla: str,
    q: str,
    *,
    limite: int = 10,
    detalle: bool = False,
    para_armar_al: date | None = None,
) -> list[Sugerencia]:
    """Las filas de `tabla` que coinciden con `q`, por relevancia y cortadas en `limite`.

    Con menos de `LARGO_MINIMO` letras (sin contar los bordes) no busca y devuelve `[]`. Una `tabla`
    que no es de `TABLAS` es un `LookupError`. `detalle` y `para_armar_al` solo cuentan en
    `insumos` y `salarios_cct` (ver la cabecera del módulo).
    """
    if tabla not in TABLAS:
        raise LookupError("tabla de consulta desconocida")
    recortado = q.strip()
    if len(recortado) < LARGO_MINIMO:
        return []
    texto = normalizar_texto(recortado)
    if tabla == "partidas_viales":
        return _partidas_viales(texto, limite)
    if tabla in ("insumos", "salarios_cct"):
        tipos = TIPOS_DE_INSUMO if tabla == "insumos" else (TIPO_MANO_DE_OBRA,)
        return _insumos(sesion, tipos, texto, limite, detalle=detalle, para_armar_al=para_armar_al)
    return _tasas(sesion, texto, limite)


# --- Lo ya usado en la carpeta (AC4) -----------------------------------------------------------


@dataclass(frozen=True)
class UnidadUsada:
    """Una unidad del catálogo en su forma canónica, cuántas filas la usan y cómo está escrita."""

    unidad: str
    usos: int
    grafias: tuple[str, ...]


@dataclass(frozen=True)
class ProveedorUsado:
    """Un proveedor de las cotizaciones, como en la más reciente, y la fecha de esa cotización."""

    proveedor: str
    ultimo_uso: date


def unidades_usadas(sesion: Session) -> list[UnidadUsada]:
    """Las unidades de las partidas y los insumos, agrupadas con `normalizar_unidad` (ver la
    cabecera). Una fila sin unidad o con la unidad en blanco no cuenta."""
    usos: dict[str, int] = {}
    grafias: dict[str, set[str]] = {}
    escritas = [
        *sesion.scalars(select(models.Partida.unidad)),
        *sesion.scalars(select(models.Insumo.unidad)),
    ]
    for escrita in escritas:
        recortada = (escrita or "").strip()
        if not recortada:
            continue
        unidad = normalizar_unidad(recortada)
        usos[unidad] = usos.get(unidad, 0) + 1
        grafias.setdefault(unidad, set()).add(recortada)
    return [
        UnidadUsada(unidad, usos[unidad], tuple(sorted(grafias[unidad])))
        for unidad in sorted(usos, key=lambda u: (-usos[u], u))
    ]


def _listas_de_las_versiones_vigentes():
    """Las listas de precios de la versión vigente de cada obra (la de mayor id no descartada)."""
    descartada = exists().where(models.DescarteVersion.presupuesto_id == models.Presupuesto.id)
    vigentes = (
        select(func.max(models.Presupuesto.id))
        .where(~descartada)
        .group_by(models.Presupuesto.proyecto_id)
    )
    return select(models.Presupuesto.lista_precios_id).where(models.Presupuesto.id.in_(vigentes))


def proveedores_usados(sesion: Session) -> list[ProveedorUsado]:
    """Los proveedores de las cotizaciones activas de la carpeta, sin repetir (ver la cabecera). A
    igual fecha manda la cotización registrada después."""
    recientes: dict[str, ProveedorUsado] = {}
    consulta = (
        select(models.Cotizacion.proveedor, models.Cotizacion.fecha)
        .where(models.Cotizacion.lista_id.in_(_listas_de_las_versiones_vigentes()))
        .order_by(models.Cotizacion.fecha, models.Cotizacion.id)
    )
    for proveedor, fecha in sesion.execute(consulta):
        escrito = " ".join(proveedor.split())
        if escrito:
            recientes[normalizar_texto(escrito)] = ProveedorUsado(escrito, fecha)
    return sorted(
        recientes.values(),
        key=lambda p: (-p.ultimo_uso.toordinal(), normalizar_texto(p.proveedor)),
    )
