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

Sin Streamlit ni FastAPI; solo lee.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.vial.constantes import PARTIDAS_VIALES
from aplicacion.busqueda import LARGO_MINIMO, rango
from core import models
from core.catalog.indices import SERIE_USD_VENTA, UNIDAD_TASA
from core.verification.texto import normalizar_texto

__all__ = ["TABLAS", "Sugerencia", "buscar"]

TABLAS = ("partidas_viales", "insumos", "tasa_bcv", "salarios_cct")

FUENTE_PARTIDAS = "Partidas viales de Sílice"
FUENTE_CATALOGO = "Catálogo de la carpeta de trabajo"
TIPOS_DE_INSUMO = ("material", "equipo")
TIPO_MANO_DE_OBRA = "mano_obra"


@dataclass(frozen=True)
class Sugerencia:
    """Una fila ofrecida: lo que se guarda, lo que se lee y de dónde sale."""

    valor: str
    etiqueta: str
    fuente: str


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


def _insumos(sesion: Session, tipos: tuple[str, ...], texto: str, limite: int) -> list[Sugerencia]:
    filas = []
    for insumo in sesion.scalars(select(models.Insumo).where(models.Insumo.tipo.in_(tipos))):
        unidad = f", {insumo.unidad}" if insumo.unidad else ""
        etiqueta = f"{insumo.descripcion} ({insumo.codigo}{unidad})"
        fuente = f"{FUENTE_CATALOGO}: {insumo.tipo.replace('_', ' ')}"
        filas.append(
            (insumo.codigo, insumo.descripcion, Sugerencia(insumo.codigo, etiqueta, fuente))
        )
    return _por_codigo_y_descripcion(filas, texto, limite)


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


def buscar(sesion: Session, tabla: str, q: str, *, limite: int = 10) -> list[Sugerencia]:
    """Las filas de `tabla` que coinciden con `q`, por relevancia y cortadas en `limite`.

    Con menos de `LARGO_MINIMO` letras (sin contar los bordes) no busca y devuelve `[]`. Una `tabla`
    que no es de `TABLAS` es un `LookupError`.
    """
    if tabla not in TABLAS:
        raise LookupError("tabla de consulta desconocida")
    recortado = q.strip()
    if len(recortado) < LARGO_MINIMO:
        return []
    texto = normalizar_texto(recortado)
    if tabla == "partidas_viales":
        return _partidas_viales(texto, limite)
    if tabla == "insumos":
        return _insumos(sesion, TIPOS_DE_INSUMO, texto, limite)
    if tabla == "salarios_cct":
        return _insumos(sesion, (TIPO_MANO_DE_OBRA,), texto, limite)
    return _tasas(sesion, texto, limite)
