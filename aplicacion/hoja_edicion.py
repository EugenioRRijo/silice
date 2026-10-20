"""Editar el borrador vivo de la hoja del proyecto (T10, 3c-1 a 3c-3; diseno §3.2 y §5.1).

Son las pestañas editables de la pagina clasica hechas servicio: el espacio (`_pestana_espacio`,
P:1213-1217), las cantidades escritas a mano (P:1760-1773), los parametros (P:2040-2053), el plan
(P:1808-1827 y `_crear_plan`), el APU de una partida (P:1633-1677) y el cambio de insumo de una
linea (P:1503-1584) pasan por la MISMA validacion de la copia `aplicacion.hoja`
(`espacio_desde_filas`, `cantidades_desde_filas`, `parametros_desde_texto`, `plan_desde_filas`,
`con_plan_secuencial`, `composicion_con_cantidades`, `cambiar_insumo`, sin reimplementarlas) y, si
el borrador cambia, por
`hoja.completar_composiciones` (la partida nueva toma su APU del catalogo, con la lista de precios
de la version abierta: `_poner_borrador`, P:256-275) antes de reemplazar al vivo subiendo su `rev`.

Si algo falla (`rev` viejo, borrador ya guardado, dato invalido, estado de la ruta, la base) el
borrador queda EXACTAMENTE como estaba y `rev` no sube: «la hoja sigue con el ultimo borrador
valido». Una edicion que deja el borrador igual tampoco sube `rev` (la clasica no hace nada si
`nuevo == borrador`). Aqui no se escribe nada en la base: solo se lee el catalogo del caso.

Orden de bloqueos (el mismo en las siete): primero el cerrojo del borrador y, DENTRO, el del
registro (`obtener`, `reemplazar`); nunca al reves. Dos peticiones con el mismo `rev` compiten por
ese cerrojo: la primera sube el `rev` y la segunda ve `RevDesactualizado` (3c-B13).

Tambien lee: los candidatos de insumo (E8), la lista de cambios (E9) y los borradores que se pueden
retomar o que estorban al abrir la misma version (E10, E11).

Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion import hoja, hoja_borradores, hoja_vista
from aplicacion.composicion import texto_de_celda
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorVivo, RevDesactualizado
from core import models
from core.budget import PeriodoPlan
from core.catalog import Catalogo

__all__ = [
    "LIMITE_INSUMOS",
    "BorradorYaGuardado",
    "PartidaSinApu",
    "RevDesactualizado",
    "SinPlan",
    "SinVersionAbierta",
    "YaTienePlan",
    "borradores_para_retomar",
    "cambiar_insumo_de_linea",
    "cambios_del_borrador",
    "candidatos_de_insumo",
    "crear_plan_secuencial",
    "descartar_de_la_version",
    "editar_apu",
    "editar_cantidades",
    "editar_espacio",
    "editar_parametros",
    "editar_plan",
    "pendiente_de_la_version",
]

#: Insumos que ofrece el selector de una linea; con mas, la clasica pide acotar por descripcion
#: (`LIMITE_INSUMOS`, P:1515).
LIMITE_INSUMOS = 300

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
#: La matriz del plan es completa (una fila por partida, como la clasica): ni mas ni menos.
MENSAJE_MATRIZ_COMPLETA = (
    "plan: la matriz debe traer exactamente las partidas del presupuesto, una fila por cada una: "
    "vuelva a cargarla."
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


class SinVersionAbierta(Exception):  # noqa: N818
    """Los insumos se eligen de la lista de precios de una version GUARDADA: el borrador en blanco
    de un proyecto sin versiones no tiene lista."""


class PartidaSinApu(Exception):  # noqa: N818
    """La partida no esta entre las composiciones del borrador."""


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
    `HojaInvalida` (cada una sumaria 1 y la ejecucion se duplicaria), y la matriz debe cubrir
    EXACTAMENTE las partidas valoradas del presupuesto (las filas de la vista): una desconocida o
    una que falta es `HojaInvalida` y el plan no queda parcial. Si la matriz describe el
    mismo plan que el vigente (aunque ordene distinto las partidas de un periodo), no hay cambio.
    """

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        borrador = vivo.borrador
        if borrador.plan is None:
            raise SinPlan
        con_codigo = [p for p in (texto_de_celda(fila, "partida") for fila in filas) if p]
        if len(set(con_codigo)) != len(con_codigo):
            raise HojaInvalida(MENSAJE_PARTIDA_REPETIDA)
        vigente, _ = hoja_vista.calculo(vivo)
        valoradas = {p.item.codigo_partida for p in vigente.elaboracion.presupuesto.partidas}
        if set(con_codigo) != valoradas:
            raise HojaInvalida(MENSAJE_MATRIZ_COMPLETA)
        plan = tuple(hoja.plan_desde_filas(filas, etiquetas))
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


# --- el APU de una partida y el cambio de insumo (3c-3) ----------------------------------------


def editar_apu(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    partida: str,
    rendimiento: str,
    materiales: Sequence[str],
    equipos: Sequence[str],
    mano_obra: Sequence[str],
) -> BorradorVivo:
    """Escribe el rendimiento y la cantidad de cada linea del APU de `partida` (P:1633-1677).

    `materiales`, `equipos` y `mano_obra` traen una cantidad (texto) por linea, en el orden del
    APU; `composicion_con_cantidades` valida con el texto de la clasica (cuenta de lineas, negativa,
    decimal). `PartidaSinApu` si la partida no tiene composicion en el borrador. Un APU igual al
    vigente no es cambio.
    """

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        borrador = vivo.borrador
        actual = borrador.composiciones.get(partida)
        if actual is None:
            raise PartidaSinApu
        nueva = hoja.composicion_con_cantidades(
            actual,
            [{"cantidad": c} for c in materiales],
            [{"cantidad": c} for c in equipos],
            [{"cantidad": c} for c in mano_obra],
            rendimiento,
        )
        if nueva == actual:
            return None
        return replace(borrador, composiciones={**borrador.composiciones, partida: nueva})

    return _cambiar(sesion, huella, id, rev, construir)


def _insumo_de_la_lista(
    sesion: Session, abierta: hoja.VersionAbierta, tipo: str, codigo: str
) -> hoja.FilaInsumo:
    """El insumo `codigo` de `tipo` con el precio de la lista de la version abierta, o
    `HojaInvalida`: solo se elige entre los que esa lista valora (P:1540-1577)."""
    lista = hoja.lista_de_version(sesion, abierta.proyecto, abierta.codigo)
    fila = sesion.execute(
        select(models.Insumo, models.PrecioInsumo.precio)
        .join(models.PrecioInsumo, models.PrecioInsumo.insumo_id == models.Insumo.id)
        .where(
            models.PrecioInsumo.lista_id == lista.id,
            models.Insumo.tipo == tipo,
            models.Insumo.codigo == codigo,
        )
        .order_by(models.Insumo.id)
    ).first()
    if fila is None:
        raise HojaInvalida(
            f"El insumo {codigo!r} no esta en la lista de precios de la version {abierta.codigo} "
            f"(o no es de tipo {tipo}): elijalo de la lista."
        )
    insumo, precio = fila
    return hoja.FilaInsumo(insumo.codigo, insumo.descripcion, insumo.unidad or "", precio)


def _lineas_del_rubro(composicion, tipo: str) -> int | None:
    """Cuantas lineas tiene el rubro `tipo` del APU, o `None` si no es un tipo de linea."""
    grupos = {
        "material": composicion.materiales,
        "equipo": composicion.equipos,
        "mano_obra": composicion.mano_obra,
    }
    return len(grupos[tipo]) if tipo in grupos else None


def cambiar_insumo_de_linea(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    partida: str,
    tipo: str,
    indice: int,
    insumo: str,
) -> BorradorVivo:
    """La linea `indice` (desde 0) del rubro `tipo` del APU de `partida` pasa al insumo `insumo`
    (su codigo) de la lista de la version abierta: toma descripcion, unidad y precio y conserva la
    cantidad (`cambiar_insumo`, P:1503-1512).

    Orden: `SinVersionAbierta` (409), `PartidaSinApu` (404) y el contenido: el tipo y la linea con
    el texto de la clasica, luego el insumo en la lista.
    """

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        borrador = vivo.borrador
        if vivo.abierta is None:
            raise SinVersionAbierta
        actual = borrador.composiciones.get(partida)
        if actual is None:
            raise PartidaSinApu
        lineas = _lineas_del_rubro(actual, tipo)
        if lineas is None or not 0 <= indice < lineas:
            # el texto de la clasica para un tipo o una linea que no existen (sin usar el insumo)
            hoja.cambiar_insumo(actual, tipo, indice, hoja.FilaInsumo("", "", "", Decimal(0)))
        elegido = _insumo_de_la_lista(sesion, vivo.abierta, tipo, insumo)
        nueva = hoja.cambiar_insumo(actual, tipo, indice, elegido)
        if nueva == actual:
            return None
        return replace(borrador, composiciones={**borrador.composiciones, partida: nueva})

    return _cambiar(sesion, huella, id, rev, construir)


# --- lo que se lee: candidatos, cambios, retomar (3c-3) ----------------------------------------


def candidatos_de_insumo(
    sesion: Session, vivo: BorradorVivo, tipo: str, texto: str, limite: int
) -> tuple[list[hoja.FilaInsumo], bool]:
    """Los insumos de `tipo` que la lista de la version abierta valora y cuya descripcion contiene
    `texto` (a lo sumo `limite`, ordenados por descripcion) y si habia mas (`insumos_candidatos`,
    P:1537-1566). `SinVersionAbierta` si el borrador no viene de una version."""
    if vivo.abierta is None:
        raise SinVersionAbierta
    filas = hoja.insumos_candidatos(
        sesion, vivo.abierta.proyecto, vivo.abierta.codigo, tipo, texto, limite=limite + 1
    )
    return filas[:limite], len(filas) > limite


def cambios_del_borrador(vivo: BorradorVivo) -> tuple[int, list[hoja.CambioEditado]]:
    """El `rev` y los `cambios_entre(version abierta, borrador)` (los que cuenta el resumen)."""
    with vivo.cerrojo:
        _, cambios = hoja_vista.calculo(vivo)
        return vivo.rev, list(cambios)


def borradores_para_retomar(huella: str, caso: str) -> list[tuple[BorradorVivo, int]]:
    """Los borradores de la ficha abiertos en `caso` (sin los ya guardados), el usado mas
    recientemente primero, cada uno con su cuenta de cambios. Listar no renueva ningun plazo."""
    return [
        (vivo, len(cambios_del_borrador(vivo)[1]))
        for vivo in hoja_borradores.listar(huella)
        if vivo.caso == caso and vivo.guardado_como is None
    ]


def _de_la_version(huella: str, caso: str, proyecto: str, version: str | None):
    return [
        vivo
        for vivo, _ in borradores_para_retomar(huella, caso)
        if vivo.proyecto == proyecto and vivo.version == version
    ]


def pendiente_de_la_version(
    huella: str, caso: str, proyecto: str, version: str | None
) -> tuple[BorradorVivo, int] | None:
    """El borrador mas reciente de esa `(proyecto, version)` con cambios sin guardar y su cuenta,
    o `None` si no hay (uno sin cambios no estorba: P:443-446)."""
    for vivo in _de_la_version(huella, caso, proyecto, version):
        cambios = len(cambios_del_borrador(vivo)[1])
        if cambios:
            return vivo, cambios
    return None


def descartar_de_la_version(huella: str, caso: str, proyecto: str, version: str | None) -> None:
    """Descarta los borradores de la ficha de esa `(proyecto, version)`: abrirla de nuevo los
    reemplaza (con `reemplazar`, o porque no tenian cambios)."""
    for vivo in _de_la_version(huella, caso, proyecto, version):
        hoja_borradores.descartar(huella, vivo.id)
