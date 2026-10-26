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

Tarea 9 (montar un presupuesto): `agregar` y `quitar` partidas a mano (`aplicacion.hoja_partidas`)
pasan por el mismo `_cambiar`. La composicion de una partida nueva sale de la lista de la version
abierta o, en un borrador en blanco, de la lista para armar de la carpeta, convertida en memoria con
la tasa del BCV si la obra esta en la otra moneda (foco de revision 1). Aqui no se escribe la lista
convertida: la escribe el guardado, a nombre de quien guarda, y toma de ella los precios de los APU;
sin tasa de los ultimos 7 dias o sin lista para armar, `SinListaDeLaObra` y el borrador no cambia.

Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion import hoja, hoja_borradores, hoja_lineas_apu, hoja_vista
from aplicacion.cifras import BLANCOS, MENSAJE_CIFRA, CifraInvalida, cifra_escrita
from aplicacion.composicion import texto_de_celda
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorVivo, RevDesactualizado
from aplicacion.hoja_lineas_apu import SinVersionGuardada
from aplicacion.hoja_partidas import (
    CalculoInvalido,
    PartidaElegida,
    agregar_partida,
    quitar_partida,
)
from aplicacion.listas_para_armar import valoracion_de_la_obra
from aplicacion.plan_rendimientos import (
    CuadrillasInvalidas,
    PlanDemasiadoLargo,
    Unidad,
    cuadrillas_escritas,
    plan_del_borrador,
)
from core import models
from core.budget import PeriodoPlan
from core.catalog import Catalogo
from core.contracts.dominio import Dominio

__all__ = [
    "LIMITE_INSUMOS",
    "BorradorYaGuardado",
    "PartidaFueraDelCatalogo",
    "PartidaSinApu",
    "RevDesactualizado",
    "SinListaDeLaObra",
    "SinPlan",
    "SinVersionAbierta",
    "SinVersionGuardada",
    "YaTienePlan",
    "agregar",
    "agregar_linea_apu",
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
    "plan_desde_rendimientos",
    "quitar",
    "quitar_linea_apu",
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
#: Las cuadrillas y las paralelas nombran partidas de la vista del plan: una ajena solo llega de
#: una ventana con otro presupuesto.
MENSAJE_PARTIDA_AJENA = (
    "Las cuadrillas o las partidas en paralelo nombran una partida que no está en el "
    "presupuesto: vuelva a cargar el plan."
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


class PartidaFueraDelCatalogo(Exception):  # noqa: N818
    """La partida que se quiere agregar no esta en el catalogo de la carpeta."""

    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo

    def __str__(self) -> str:
        return f"La partida «{self.codigo}» no está en el catálogo: compóngala primero en Componer."


class SinListaDeLaObra(Exception):  # noqa: N818
    """No hay lista con que valorar la obra (sin lista para armar o, en la otra moneda, sin tasa
    del BCV de los ultimos 7 dias); el mensaje es el que ve la persona."""


def _completar(sesion: Session, vivo: BorradorVivo, nuevo: hoja.Borrador) -> hoja.Borrador:
    """`nuevo` con la composicion de cada partida nueva que el catalogo conoce, con la lista de la
    version abierta o, en blanco, con la de la obra a la fecha del borrador
    (`valoracion_de_la_obra`). En blanco no se busca lista si no hay partidas nuevas, y nada se
    escribe: en la otra moneda, el APU de la lista para armar se convierte con la tasa del BCV
    (`hoja.composicion_convertida`, la misma cuenta que la lista convertida); la lista convertida
    la escribe el guardado, que vuelve a tomar los precios de ella."""
    if vivo.abierta is not None:
        lista = hoja.lista_de_version(sesion, vivo.abierta.proyecto, vivo.abierta.codigo)
        return hoja.completar_composiciones(Catalogo(sesion), nuevo, lista=lista)
    nuevas = hoja.partidas_sin_composicion(nuevo)
    if not nuevas:
        return nuevo
    try:
        valoracion = valoracion_de_la_obra(sesion, vivo.proyecto, nuevo.fecha)
    except ValueError as error:  # SinListaParaArmar (sin lista o sin tasa) u obra que no existe
        raise SinListaDeLaObra(str(error)) from None
    completo = hoja.completar_composiciones(Catalogo(sesion), nuevo, lista=valoracion.base)
    if valoracion.tasa is None:
        return completo
    de, a, tasa = valoracion.base.moneda, valoracion.moneda, valoracion.tasa.valor
    return replace(
        completo,
        composiciones={
            codigo: hoja.composicion_convertida(apu, de, a, tasa) if codigo in nuevas else apu
            for codigo, apu in completo.composiciones.items()
        },
    )


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
        return hoja_borradores.reemplazar(huella, id, _completar(sesion, vivo, nuevo), rev)


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
            vivo.borrador,
            espacio=hoja.espacio_desde_filas(tablas, base=vivo.borrador.espacio, tecleado=True),
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
            # lo no enviado se escribe como lo teclearia la persona (coma decimal): se lee igual
            {"clave": clave, "cantidad": enviadas.get(clave, hoja.texto_editable(item.cantidad))}
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


def plan_desde_rendimientos(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    *,
    cuadrillas: Mapping[str, str],
    paralelas: Sequence[str],
    unidad: Unidad,
) -> tuple[BorradorVivo, list[str]]:
    """Rehace el plan del borrador desde los rendimientos (Tarea 21) y devuelve el borrador y los
    avisos de las partidas sin rendimiento o con cantidad 0.

    Vale con plan o sin el: reemplaza la matriz entera. `cuadrillas` trae el texto tecleado por
    partida (1 si falta); `paralelas`, las que empiezan con la anterior. Una partida que no esta
    entre los renglones, unas cuadrillas que no son un entero de 1 a 99 o un plan de mas de 500
    periodos son `HojaInvalida` y el borrador no cambia. El mismo plan no sube el `rev`.
    """
    avisos: list[str] = []

    def construir(vivo: BorradorVivo) -> hoja.Borrador | None:
        borrador = vivo.borrador
        items = hoja.items_elaborados(borrador)
        codigos = {i.codigo_partida for i in items}
        if not (set(cuadrillas) | set(paralelas)) <= codigos:
            raise HojaInvalida(MENSAJE_PARTIDA_AJENA)
        try:
            plan, encontrados = plan_del_borrador(
                items,
                borrador.composiciones,
                cuadrillas=cuadrillas_escritas(cuadrillas),
                paralelas=frozenset(paralelas),
                unidad=unidad,
            )
        except (CuadrillasInvalidas, PlanDemasiadoLargo) as error:
            raise HojaInvalida(str(error)) from None
        avisos.extend(encontrados)
        if borrador.plan is not None and _canonico(plan) == _canonico(borrador.plan):
            return None
        return replace(borrador, plan=tuple(plan))

    return _cambiar(sesion, huella, id, rev, construir), avisos


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


# --- agregar y quitar lineas del APU de la version (Tarea 26) ------------------------------------

#: Un codigo que la lista de la version no valora (el texto propio, sin repetir lo enviado).
MENSAJE_INSUMO_FUERA = (
    "Ese insumo no está en la lista de precios de la versión: elíjalo de la lista."
)


def _cifra_de_linea(texto: str, nombre: str, falta: str) -> Decimal:
    """Una cifra tecleada de la linea nueva con la regla de las cifras; el texto del error empieza
    por el campo («La cantidad…», «Escriba el precio…») y no repite lo escrito."""
    try:
        return cifra_escrita(texto)
    except CifraInvalida:
        if not texto.strip(BLANCOS):
            raise HojaInvalida(f"{falta} {MENSAJE_CIFRA}") from None
        raise HojaInvalida(f"{nombre} no se entiende como número. {MENSAJE_CIFRA}") from None


def _apu_de_la_version(vivo: BorradorVivo, partida: str):
    """El APU de `partida` en el borrador de una version guardada (`SinVersionGuardada`,
    `PartidaSinApu`)."""
    if vivo.abierta is None:
        raise SinVersionGuardada
    actual = vivo.borrador.composiciones.get(partida)
    if actual is None:
        raise PartidaSinApu
    return actual


def agregar_linea_apu(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    partida: str,
    *,
    tipo: str,
    insumo: str,
    descripcion: str,
    unidad: str,
    cantidad: str,
    precio: str,
    depreciacion: str,
    modalidad: str,
) -> BorradorVivo:
    """Agrega al APU de `partida` una linea de `tipo` al final de su rubro (Tarea 26).

    Con `insumo` (su codigo), un insumo de la lista de la version abierta: toma su descripcion, su
    unidad y su precio (lo tecleado en esos campos no cuenta). Sin el, uno nuevo con la
    `descripcion`, la `unidad` (material) y el `precio` tecleados. La cantidad, el precio y la
    depreciacion (equipo) se leen con la regla de las cifras; la modalidad es la de la mano de
    obra. Orden: `SinVersionGuardada` (409), `PartidaSinApu` (404) y `HojaInvalida` (422) con el
    texto de `hoja_lineas_apu.agregar_linea`. Si algo falla, el borrador no cambia."""

    def construir(vivo: BorradorVivo) -> hoja.Borrador:
        actual = _apu_de_la_version(vivo, partida)
        if tipo not in hoja.TIPOS_DE_LINEA:
            raise HojaInvalida(hoja_lineas_apu.MENSAJE_TIPO)
        if insumo.strip():
            assert vivo.abierta is not None  # lo exige `_apu_de_la_version`
            try:
                elegido = _insumo_de_la_lista(sesion, vivo.abierta, tipo, insumo.strip())
            except HojaInvalida:
                raise HojaInvalida(MENSAJE_INSUMO_FUERA) from None
            nombre, medida, valor = elegido.descripcion, elegido.unidad, elegido.precio
        else:
            nombre, medida = descripcion, unidad
            valor = None
        cuanto = _cifra_de_linea(cantidad, "La cantidad", "Escriba la cantidad.")
        if valor is None:
            valor = _cifra_de_linea(precio, "El precio", "Escriba el precio del insumo nuevo.")
        fraccion = None
        if tipo == "equipo":
            fraccion = _cifra_de_linea(
                depreciacion,
                "La depreciación",
                "Escriba la depreciación del equipo, por ejemplo 0,005.",
            )
        nueva = hoja_lineas_apu.agregar_linea(
            actual,
            tipo,
            descripcion=nombre,
            unidad=medida,
            cantidad=cuanto,
            precio=valor,
            depreciacion=fraccion,
            modalidad=modalidad,
        )
        borrador = vivo.borrador
        return replace(borrador, composiciones={**borrador.composiciones, partida: nueva})

    return _cambiar(sesion, huella, id, rev, construir)


def quitar_linea_apu(
    sesion: Session, huella: str, id: str, rev: int, partida: str, tipo: str, indice: int
) -> BorradorVivo:
    """Quita la linea `indice` (desde 0) del rubro `tipo` del APU de `partida` (Tarea 26).
    `SinVersionGuardada` (409), `PartidaSinApu` (404) y `HojaInvalida` (422: la linea ya no esta,
    o era la ultima del APU). Si algo falla, el borrador no cambia."""

    def construir(vivo: BorradorVivo) -> hoja.Borrador:
        actual = _apu_de_la_version(vivo, partida)
        nueva = hoja_lineas_apu.quitar_linea(actual, tipo, indice)
        borrador = vivo.borrador
        return replace(borrador, composiciones={**borrador.composiciones, partida: nueva})

    return _cambiar(sesion, huella, id, rev, construir)


# --- partidas agregadas y quitadas a mano (Tarea 9) ---------------------------------------------


def _partida_del_catalogo(sesion: Session, codigo: str) -> PartidaElegida:
    """La partida `codigo` del catalogo de la carpeta, o `PartidaFueraDelCatalogo`."""
    try:
        fila = Catalogo(sesion).partida(codigo)
    except KeyError:
        raise PartidaFueraDelCatalogo(codigo) from None
    try:
        dominio = Dominio(fila.dominio)
    except ValueError:  # una partida sin dominio declarado se presupuesta como obra civil
        dominio = Dominio.CIVIL
    return PartidaElegida(fila.codigo, fila.descripcion, fila.unidad, dominio)


def agregar(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    *,
    codigo: str,
    cantidad: str,
    calculo: str,
    nota: str,
) -> tuple[BorradorVivo, str]:
    """Agrega al borrador la partida `codigo` del catalogo con su cantidad, su calculo y su nota
    (`hoja_partidas.agregar_partida`) y devuelve el borrador y la clave del renglon nuevo.

    Orden: ya guardado, `rev`, la partida en el catalogo (`PartidaFueraDelCatalogo`), la cantidad
    y el calculo (`HojaInvalida` con el texto de la regla de las cifras o de la Tarea 8) y la lista
    de la obra (`SinListaDeLaObra`). Si algo falla, el borrador no cambia."""
    clave: list[str] = []

    def construir(vivo: BorradorVivo) -> hoja.Borrador:
        partida = _partida_del_catalogo(sesion, codigo)
        try:
            nuevo, nueva = agregar_partida(
                vivo.borrador, partida, cantidad=cantidad, calculo=calculo, nota=nota
            )
        except (CalculoInvalido, CifraInvalida) as error:
            raise HojaInvalida(str(error)) from None
        clave.append(nueva)
        return nuevo

    return _cambiar(sesion, huella, id, rev, construir), clave[0]


def quitar(sesion: Session, huella: str, id: str, rev: int, clave: str) -> BorradorVivo:
    """Quita del borrador el renglon `clave`, con su cantidad escrita y su nota
    (`hoja_partidas.quitar_partida`): solo los de la version; uno del espacio es `HojaInvalida`."""
    return _cambiar(sesion, huella, id, rev, lambda vivo: quitar_partida(vivo.borrador, clave))


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
