"""Editar el borrador vivo de la hoja del proyecto (T10, 3c-1 y 3c-2; diseno §3.2 y §5.1).

Son las pestañas editables de la pagina clasica hechas servicio: el espacio (`_pestana_espacio`,
P:1213-1217), las cantidades escritas a mano (P:1760-1773), los parametros (P:2040-2053) y el plan
(P:1808-1827 y `_crear_plan`) pasan por la MISMA validacion de la copia `aplicacion.hoja`
(`espacio_desde_filas`, `cantidades_desde_filas`, `parametros_desde_texto`, `plan_desde_filas`,
`con_plan_secuencial`, sin reimplementarlas) y, si el borrador cambia, por
`hoja.completar_composiciones` (la partida nueva toma su APU del catalogo, con la lista de precios
de la version abierta: `_poner_borrador`, P:256-275) antes de reemplazar al vivo subiendo su `rev`.

Si algo falla (`rev` viejo, borrador ya guardado, dato invalido, estado de la ruta, la base) el
borrador queda EXACTAMENTE como estaba y `rev` no sube: «la hoja sigue con el ultimo borrador
valido». Una edicion que deja el borrador igual tampoco sube `rev` (la clasica no hace nada si
`nuevo == borrador`). Aqui no se escribe nada en la base: solo se lee el catalogo del caso.

Orden de bloqueos (el mismo en las cinco): primero el cerrojo del borrador y, DENTRO, el del
registro (`obtener`, `reemplazar`); nunca al reves.

Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace

from sqlalchemy.orm import Session

from aplicacion import hoja, hoja_borradores, hoja_vista
from aplicacion.composicion import texto_de_celda
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorVivo, RevDesactualizado
from core.budget import PeriodoPlan
from core.catalog import Catalogo

__all__ = [
    "BorradorYaGuardado",
    "RevDesactualizado",
    "SinPlan",
    "YaTienePlan",
    "crear_plan_secuencial",
    "editar_cantidades",
    "editar_espacio",
    "editar_parametros",
    "editar_plan",
]

#: Las cinco tablas del editor del espacio, como las envia el navegador: tabla -> filas de texto.
TablasDelEspacio = Mapping[str, Sequence[Mapping[str, str]]]

#: Una clave que no es de ningun renglon, o repetida: el navegador manda la clave que le dio la
#: vista, asi que solo ocurre con un presupuesto distinto del que vio.
MENSAJE_RENGLONES = (
    "Las cantidades enviadas no corresponden a los renglones del presupuesto: vuelva a cargarlo."
)
MENSAJE_PARTIDA_REPETIDA = (
    "plan: una partida aparece en más de una fila; deje una sola fila por partida."
)


class BorradorYaGuardado(Exception):  # noqa: N818
    """El borrador ya se guardo como una version (3d): se abre esa version para seguir."""

    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo


class SinPlan(Exception):  # noqa: N818
    """Se edita la matriz del plan de un borrador que no tiene plan: se crea el secuencial."""


class YaTienePlan(Exception):  # noqa: N818
    """Se pide el plan secuencial de un borrador que ya tiene plan: se edita la matriz."""


def _cambiar(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    construir: Callable[[BorradorVivo], hoja.Borrador | None],
) -> BorradorVivo:
    """El nucleo comun de las cinco ediciones (`_poner_borrador`, P:256-275).

    Dentro del cerrojo del borrador: ya guardado, `rev` (ANTES que el contenido: una ventana
    rezagada debe recargar, no corregir datos), `construir` (que lanza `HojaInvalida` o el error de
    estado de la ruta y devuelve el borrador nuevo, o `None` si no hay nada que cambiar) y, si el
    borrador cambia, `completar_composiciones` y el reemplazo.
    """
    vivo = hoja_borradores.obtener(huella, id)
    with vivo.cerrojo:
        if vivo.guardado_como is not None:
            raise BorradorYaGuardado(vivo.guardado_como)
        if vivo.rev != rev:
            raise RevDesactualizado(id)
        nuevo = construir(vivo)
        if nuevo is None or nuevo == vivo.borrador:
            return vivo
        lista = None
        if vivo.abierta is not None:
            lista = hoja.lista_de_version(sesion, vivo.abierta.proyecto, vivo.abierta.codigo)
        nuevo = hoja.completar_composiciones(Catalogo(sesion), nuevo, lista=lista)
        return hoja_borradores.reemplazar(huella, id, nuevo, rev)


def editar_espacio(
    sesion: Session, huella: str, id: str, rev: int, tablas: TablasDelEspacio
) -> BorradorVivo:
    """Aplica las tablas al espacio del borrador `id` de la ficha `huella` y lo devuelve.

    Lanza `BorradorInexistente` (no existe para la ficha), `BorradorYaGuardado`,
    `RevDesactualizado` o `HojaInvalida` con el texto de la clasica (P:1213-1217).
    """
    return _cambiar(
        sesion,
        huella,
        id,
        rev,
        lambda vivo: replace(
            vivo.borrador, espacio=hoja.espacio_desde_filas(tablas, base=vivo.borrador.espacio)
        ),
    )


def editar_cantidades(
    sesion: Session, huella: str, id: str, rev: int, filas: Sequence[Mapping[str, str]]
) -> BorradorVivo:
    """Escribe a mano las cantidades de los renglones tocados (`filas`: `clave` y `cantidad`).

    El navegador manda solo lo tocado; aqui se arma la tabla COMPLETA en el orden de
    `items_sin_escribir` (cada renglon no enviado conserva su cantidad vigente, escrita o
    calculada) para que `fila {n}` del error sea la posicion del renglon en el presupuesto, como en
    la clasica (P:1760-1773). Un valor igual al calculado deja de ser «escrito». Una clave que no es
    de ningun renglon, o repetida, es `HojaInvalida` (la clasica la ignoraba en silencio).
    """

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        borrador = vivo.borrador
        items = hoja.items_sin_escribir(borrador)
        claves = hoja.claves_de_items(items)
        conocidas = set(claves)
        enviadas: dict[str, str] = {}
        for fila in filas:
            clave = fila["clave"]
            if clave not in conocidas or clave in enviadas:
                raise HojaInvalida(MENSAJE_RENGLONES)
            enviadas[clave] = fila["cantidad"]
        vigentes = hoja.items_elaborados(borrador)
        tabla = [
            {"clave": clave, "cantidad": enviadas.get(clave, hoja.texto_numero(item.cantidad))}
            for clave, item in zip(claves, vigentes, strict=True)
        ]
        escritas = hoja.cantidades_desde_filas(tabla, items)
        if escritas == dict(borrador.cantidades):
            return None
        return replace(borrador, cantidades=escritas)

    return _cambiar(sesion, huella, id, rev, construir)


def editar_parametros(
    sesion: Session, huella: str, id: str, rev: int, textos: Mapping[str, str]
) -> BorradorVivo:
    """Aplica los cuatro parametros de costo (P:2040-2053); un cambio valido recalcula todo."""

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        parametros = hoja.parametros_desde_texto(textos)
        if parametros == vivo.borrador.parametros:
            return None
        return replace(vivo.borrador, parametros=parametros)

    return _cambiar(sesion, huella, id, rev, construir)


def _canonico(plan: Sequence[PeriodoPlan]) -> tuple:
    """Un plan sin importar el orden de las partidas dentro de un periodo (la matriz las ordena
    por partida; el plan guardado, como se fueron escribiendo)."""
    return tuple((etiqueta, tuple(sorted(reparto))) for etiqueta, reparto in plan)


def editar_plan(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    etiquetas: Sequence[str],
    filas: Sequence[Mapping[str, object]],
) -> BorradorVivo:
    """Aplica la matriz partida por periodo (P:1808-1827). `SinPlan` si el borrador no tiene plan.

    `filas`: `{"partida": codigo, <etiqueta>: fraccion}`. Dos filas de la misma partida son
    `HojaInvalida` (cada una sumaria 1 y la ejecucion se duplicaria). Si la matriz describe el
    mismo plan que el vigente (aunque ordene distinto las partidas de un periodo), no hay cambio.
    """

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        borrador = vivo.borrador
        if borrador.plan is None:
            raise SinPlan
        con_codigo = [p for p in (texto_de_celda(fila, "partida") for fila in filas) if p]
        if len(set(con_codigo)) != len(con_codigo):
            raise HojaInvalida(MENSAJE_PARTIDA_REPETIDA)
        plan = tuple(hoja.plan_desde_filas(filas, etiquetas))
        vigente, _ = hoja_vista.calculo(vivo)
        if _canonico(plan) == _canonico(vigente.plan or ()):
            return None
        return replace(borrador, plan=plan)

    return _cambiar(sesion, huella, id, rev, construir)


def crear_plan_secuencial(sesion: Session, huella: str, id: str, rev: int) -> BorradorVivo:
    """El plan secuencial (una partida por periodo, al 100 %) para un borrador sin plan
    (`_crear_plan`, P:1796-1806). `YaTienePlan` si ya lo tiene."""

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        if vivo.borrador.plan is not None:
            raise YaTienePlan
        return hoja.con_plan_secuencial(vivo.borrador)

    return _cambiar(sesion, huella, id, rev, construir)
