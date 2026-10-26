"""La procura con fechas: qué materiales pide la obra, cuándo se necesitan, cuándo hay que pedirlos
y qué compra llegó tarde (MP-7, Tarea 23; diseño de montar un presupuesto §11, meta 3; foco 5).

- **Explosión:** solo los materiales de la composición congelada de la versión
  (`linea_composicion_version`), `Σ cantidad de la partida × cantidad de la línea`, agrupados por
  (descripción, unidad), en el orden en que aparecen en el presupuesto. Equipos y mano de obra no se
  compran. Una partida con cantidad 0 no pide nada.
- **Fechas:** con la línea base de la obra (la última declarada) sobre esa versión, `se_necesita` es
  el primer día hábil del primer período con fracción mayor que cero de la primera partida que usa
  el material (`dia_habil` del núcleo, con el calendario y los feriados de la línea base: el período
  `p`, contado desde 0, empieza en el día hábil `p × días por período + 1`). `pedir_a_mas_tardar` es
  `se_necesita` menos el plazo de entrega en días hábiles (3 por omisión; cambiable por material y
  obra). Sin línea base no hay fechas, y la procura lo dice.
- **Compras:** cada pedido y cada recepción es una fila (solo inserción) con su fecha; vale la
  primera de cada evento. La recepción con precio es además una observación de mercado de «Lo que
  compramos» (`fuente_tipo="compra"`, Tarea 13), en la moneda de la carpeta.
- **Alertas al corte** (lo que pasó después del corte no cuenta): sin pedir, desde dos días hábiles
  antes de la fecha de pedido, un aviso («Pida … antes del …»); desde esa fecha, un error; recibido
  después de la fecha en que se necesitaba, un error de compra tardía, que sugiere la causa
  «compra tardía» en la valuación de la partida.

Todo determinista, en `Decimal` y sin IA. Ninguna función confirma: escriben con `flush` y quien
llama confirma. `ReglaDeProcura` lleva el mensaje para la persona; `NoExiste` y `CarpetaSinMoneda`
son los del estudio de mercado; los demás `ValueError` son de programación.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.cifras import CifraInvalida, cifra_escrita
from aplicacion.listas_para_armar import exigir_responsable, moneda_de_la_carpeta
from aplicacion.mercado import (
    MENSAJE_SIN_MONEDA,
    CarpetaSinMoneda,
    NoExiste,
    registrar_observacion,
)
from aplicacion.proyectos import proyectos_del_caso, resolver_proyecto
from aplicacion.tablas_procura import CompraDeInsumo, PlazoDeEntrega
from core import models
from core.budget.calendario import dia_habil, es_habil
from core.budget.edicion import version_vigente
from core.budget.valuaciones import linea_base_vigente

if TYPE_CHECKING:
    from aplicacion.mesa import Pendiente

__all__ = [
    "AVISO",
    "CAUSA_COMPRA_TARDIA",
    "ERROR",
    "EVENTOS",
    "MENSAJE_PLAZO",
    "MENSAJE_SIN_LINEA_BASE",
    "PLAZO_MAXIMO",
    "PLAZO_POR_OMISION",
    "VER_LA_PROCURA",
    "AlertaDeCompra",
    "NecesidadDeInsumo",
    "Procura",
    "ReglaDeProcura",
    "alertas_de_compra",
    "causa_sugerida",
    "causas_sugeridas",
    "explosion",
    "fijar_plazo",
    "pendientes_de_compras",
    "procura",
    "registrar_compra",
]

#: Los eventos de una compra.
EVENTOS = ("pedida", "recibida")
#: Días hábiles de entrega de un material sin plazo declarado.
PLAZO_POR_OMISION = 3
PLAZO_MAXIMO = 365
#: Días hábiles antes de la fecha de pedido desde los que se avisa.
DIAS_DE_AVISO = 2
AVISO = "AVISO"
ERROR = "ERROR"
#: La clave de «Compra tardía» en las causas de retraso de la Tarea 22 (`aplicacion.causas`).
CAUSA_COMPRA_TARDIA = "compra_tardia"
#: La acción de un pendiente de compras en la mesa: la procura está en Control de obra.
VER_LA_PROCURA = ("Ver la procura", "control")
MENSAJE_SIN_LINEA_BASE = "Declare la línea base para calcular las fechas de compra."
MENSAJE_PLAZO = "El plazo de entrega es un número entero de días hábiles, de 0 a 365."
_LARGO_RESPONSABLE = 200
_LARGO_FUENTE = 200
_MATERIAL = models.TipoInsumo.MATERIAL.value

Clave = tuple[str, str]


class ReglaDeProcura(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """Lo escrito no cumple una regla de la procura; el mensaje es el que ve la persona."""


@dataclass(frozen=True)
class NecesidadDeInsumo:
    """Un material de la obra: cuánto pide la versión, qué partidas lo usan (en su orden), cuándo
    se necesita y cuándo pedirlo a más tardar (`None` sin línea base), el plazo de entrega en días
    hábiles y la primera fecha en que se pidió y en que se recibió (`None` si no consta)."""

    descripcion: str
    unidad: str
    cantidad: Decimal
    partidas: tuple[str, ...]
    se_necesita: date | None
    pedir_a_mas_tardar: date | None
    plazo: int
    pedida: date | None
    recibida: date | None


@dataclass(frozen=True)
class AlertaDeCompra:
    """`severidad` es `AVISO` o `ERROR`; `texto`, lo que ve la persona."""

    severidad: str
    texto: str


@dataclass(frozen=True)
class Procura:
    """La procura de una obra: la versión explotada (la de la línea base o, sin ella, la vigente;
    `None` si no tiene versiones), sus necesidades, los feriados de la línea base y el aviso que se
    muestra si no hay fechas."""

    version: str | None
    necesidades: tuple[NecesidadDeInsumo, ...]
    feriados: frozenset[date]
    aviso: str | None


@dataclass(frozen=True)
class _Calendario:
    inicio: date
    largo: int
    feriados: frozenset[date]


@dataclass(frozen=True)
class _Linea:
    clave: Clave
    cantidad: Decimal
    partida: str
    insumo_id: int | None


# --- lecturas -----------------------------------------------------------------------------------


def _obra(sesion: Session, proyecto: str) -> models.Proyecto:
    obra = resolver_proyecto(sesion, proyecto.strip())
    if obra is None:
        raise NoExiste(f"No hay ninguna obra «{proyecto}» en esta carpeta de trabajo.")
    return obra


def _calendario(fila: models.LineaBaseControl) -> _Calendario:
    calendario = fila.calendario
    feriados = frozenset(date.fromisoformat(dia) for dia in json.loads(calendario.feriados))
    return _Calendario(calendario.fecha_inicio, calendario.dias_por_periodo, feriados)


def _inicios(sesion: Session, version_id: int, calendario: _Calendario) -> dict[str, date]:
    """El primer día hábil de cada partida del plan de la versión (su primer período con fracción
    mayor que cero)."""
    primeros: dict[str, int] = {}
    for fila in sesion.scalars(
        select(models.PlanVersion).where(
            models.PlanVersion.presupuesto_id == version_id,
            models.PlanVersion.codigo_partida.is_not(None),
        )
    ):
        if fila.fraccion is None or fila.fraccion <= 0:
            continue
        codigo = fila.codigo_partida
        primeros[codigo] = min(fila.periodo, primeros.get(codigo, fila.periodo))
    return {
        codigo: dia_habil(calendario.inicio, periodo * calendario.largo + 1, calendario.feriados)
        for codigo, periodo in primeros.items()
    }


def _lineas(sesion: Session, version: models.Presupuesto) -> Iterator[_Linea]:
    """Cada línea de material de la versión con su cantidad total, en el orden del presupuesto."""
    cantidades: dict[str, Decimal] = {}
    for renglon in version.partidas:
        codigo = renglon.partida.codigo
        cantidades[codigo] = cantidades.get(codigo, Decimal(0)) + renglon.cantidad
    composiciones = {
        fila.codigo_partida: fila
        for fila in sesion.scalars(
            select(models.ComposicionVersion).where(
                models.ComposicionVersion.presupuesto_id == version.id
            )
        )
    }
    for codigo, cantidad in cantidades.items():
        composicion = composiciones.get(codigo)
        if composicion is None or cantidad == 0:
            continue
        for linea in composicion.lineas:
            total = cantidad * linea.cantidad
            if linea.tipo != _MATERIAL or total == 0:
                continue
            yield _Linea((linea.descripcion, linea.unidad or ""), total, codigo, linea.insumo_id)


def _primeras(sesion: Session, proyecto_id: int) -> dict[tuple[str, str, str], date]:
    """La primera fecha de cada (descripción, unidad, evento) de las compras de la obra."""
    primeras: dict[tuple[str, str, str], date] = {}
    for fila in sesion.scalars(
        select(CompraDeInsumo).where(CompraDeInsumo.proyecto_id == proyecto_id)
    ):
        clave = (fila.descripcion_insumo, fila.unidad, fila.evento)
        primeras[clave] = min(fila.fecha, primeras.get(clave, fila.fecha))
    return primeras


def _plazos(sesion: Session, proyecto_id: int) -> dict[Clave, int]:
    return {
        (fila.descripcion_insumo, fila.unidad): fila.dias
        for fila in sesion.scalars(
            select(PlazoDeEntrega).where(PlazoDeEntrega.proyecto_id == proyecto_id)
        )
    }


def _habiles_antes(fecha: date, dias: int, feriados: Collection[date]) -> date:
    """El día hábil que queda `dias` días hábiles antes de `fecha` (la misma con 0)."""
    dia = fecha
    while dias > 0:
        dia -= timedelta(days=1)
        if es_habil(dia, feriados):
            dias -= 1
    return dia


def _explotar(
    sesion: Session,
    obra: models.Proyecto,
    version: models.Presupuesto,
    calendario: _Calendario | None,
) -> tuple[NecesidadDeInsumo, ...]:
    inicios = {} if calendario is None else _inicios(sesion, version.id, calendario)
    feriados = frozenset() if calendario is None else calendario.feriados
    cantidades: dict[Clave, Decimal] = {}
    partidas: dict[Clave, list[str]] = {}
    fechas: dict[Clave, date | None] = {}
    for linea in _lineas(sesion, version):
        clave = linea.clave
        cantidades[clave] = cantidades.get(clave, Decimal(0)) + linea.cantidad
        usan = partidas.setdefault(clave, [])
        if linea.partida not in usan:
            usan.append(linea.partida)
        # La fecha más temprana de las partidas que lo usan y están en el plan.
        conocidas = [f for f in (fechas.get(clave), inicios.get(linea.partida)) if f is not None]
        fechas[clave] = min(conocidas, default=None)
    plazos = _plazos(sesion, obra.id)
    compras = _primeras(sesion, obra.id)
    necesidades = []
    for clave, cantidad in cantidades.items():
        plazo = plazos.get(clave, PLAZO_POR_OMISION)
        se_necesita = fechas[clave]
        pedir = None if se_necesita is None else _habiles_antes(se_necesita, plazo, feriados)
        necesidades.append(
            NecesidadDeInsumo(
                descripcion=clave[0],
                unidad=clave[1],
                cantidad=cantidad,
                partidas=tuple(partidas[clave]),
                se_necesita=se_necesita,
                pedir_a_mas_tardar=pedir,
                plazo=plazo,
                pedida=compras.get((*clave, "pedida")),
                recibida=compras.get((*clave, "recibida")),
            )
        )
    return tuple(necesidades)


def _linea_base(sesion: Session, obra: models.Proyecto, hasta: date = date.max):
    return linea_base_vigente(sesion, obra.nombre, hasta)


def _procura_de(sesion: Session, obra: models.Proyecto) -> Procura:
    fila = _linea_base(sesion, obra)
    if fila is None:
        version = version_vigente(sesion, obra.nombre)
        calendario = None
    else:
        version = sesion.get(models.Presupuesto, fila.presupuesto_id)
        calendario = _calendario(fila)
    aviso = MENSAJE_SIN_LINEA_BASE if calendario is None else None
    if version is None:
        return Procura(None, (), frozenset(), aviso)
    feriados = frozenset() if calendario is None else calendario.feriados
    return Procura(version.codigo, _explotar(sesion, obra, version, calendario), feriados, aviso)


def explosion(sesion: Session, proyecto: str, version: str) -> list[NecesidadDeInsumo]:
    """Los materiales de la versión `version` de la obra `proyecto` (código o nombre). Las fechas
    salen del plan de esa versión con el calendario de la línea base solo si la última línea base
    declarada es de esa versión; si no, son `None`. `NoExiste` si no hay tal obra o versión."""
    obra = _obra(sesion, proyecto)
    modelo = sesion.scalars(
        select(models.Presupuesto).where(
            models.Presupuesto.proyecto_id == obra.id, models.Presupuesto.codigo == version
        )
    ).one_or_none()
    if modelo is None:
        raise NoExiste(f"La obra «{obra.nombre}» no tiene ninguna versión «{version}».")
    fila = _linea_base(sesion, obra)
    calendario = (
        _calendario(fila) if fila is not None and fila.presupuesto_id == modelo.id else None
    )
    return list(_explotar(sesion, obra, modelo, calendario))


def procura(sesion: Session, proyecto: str) -> Procura:
    """La procura de la obra `proyecto` (código o nombre): la de la versión de su última línea
    base, con fechas; sin línea base, la de la versión vigente, sin fechas y con el aviso
    `MENSAJE_SIN_LINEA_BASE`. `NoExiste` si no hay tal obra."""
    return _procura_de(sesion, _obra(sesion, proyecto))


# --- alertas ------------------------------------------------------------------------------------


def alertas_de_compra(
    necesidades: Sequence[NecesidadDeInsumo], corte: date, feriados: Collection[date]
) -> list[AlertaDeCompra]:
    """Lo que la procura advierte al `corte`, a lo sumo una alerta por material y en su orden.

    Solo cuentan los pedidos y recepciones con fecha hasta el corte (una recepción cuenta también
    como pedido). Recibido después de `se_necesita` → `ERROR` de compra tardía; sin pedir y con el
    corte desde `pedir_a_mas_tardar` → `ERROR`; sin pedir y con el corte desde dos días hábiles
    antes (con `feriados`) → `AVISO`. Sin fechas, nada."""
    alertas = []
    for necesidad in necesidades:
        se_necesita, pedir = necesidad.se_necesita, necesidad.pedir_a_mas_tardar
        if se_necesita is None or pedir is None:
            continue
        nombre = necesidad.descripcion
        recibida = necesidad.recibida if _hasta(necesidad.recibida, corte) else None
        if recibida is not None:
            if recibida > se_necesita:
                alertas.append(
                    AlertaDeCompra(
                        ERROR,
                        f"Compra tardía: {nombre} llegó el {recibida:%d/%m/%Y} y se necesitaba "
                        f"el {se_necesita:%d/%m/%Y}.",
                    )
                )
            continue
        if _hasta(necesidad.pedida, corte):
            continue
        if corte >= pedir:
            alertas.append(
                AlertaDeCompra(
                    ERROR, f"{nombre} no está pedido y debía pedirse el {pedir:%d/%m/%Y}."
                )
            )
        elif corte >= _habiles_antes(pedir, DIAS_DE_AVISO, feriados):
            alertas.append(AlertaDeCompra(AVISO, f"Pida {nombre} antes del {pedir:%d/%m/%Y}."))
    return alertas


def _hasta(fecha: date | None, corte: date) -> bool:
    return fecha is not None and fecha <= corte


def causas_sugeridas(sesion: Session, proyecto: str, hasta: date) -> dict[str, str]:
    """Por código de partida, en el orden del presupuesto, `CAUSA_COMPRA_TARDIA` si algún material
    de la partida llegó (hasta `hasta`, la primera recepción) después del primer día de esa partida
    en el plan de la línea base vigente a `hasta`. Las partidas sin causa no aparecen; sin línea
    base, o si la partida no está en el plan, nada."""
    obra = _obra(sesion, proyecto)
    fila = _linea_base(sesion, obra, hasta)
    if fila is None:
        return {}
    version = sesion.get(models.Presupuesto, fila.presupuesto_id)
    inicios = _inicios(sesion, version.id, _calendario(fila))
    compras = _primeras(sesion, obra.id)
    sugeridas: dict[str, str] = {}
    for linea in _lineas(sesion, version):
        inicio = inicios.get(linea.partida)
        if inicio is None or linea.partida in sugeridas:
            continue
        llegada = compras.get((*linea.clave, "recibida"))
        if _hasta(llegada, hasta) and llegada > inicio:
            sugeridas[linea.partida] = CAUSA_COMPRA_TARDIA
    return sugeridas


def causa_sugerida(sesion: Session, proyecto: str, codigo_partida: str, hasta: date) -> str | None:
    """La causa que `causas_sugeridas` da a la partida `codigo_partida`, o `None`."""
    return causas_sugeridas(sesion, proyecto, hasta).get(codigo_partida)


# --- escrituras ---------------------------------------------------------------------------------


def _responsable(texto: str) -> str:
    responsable = exigir_responsable(texto)
    if len(responsable) > _LARGO_RESPONSABLE:
        raise ValueError(
            f"quien lo hace (responsable) admite hasta {_LARGO_RESPONSABLE} caracteres"
        )
    return responsable


def _material(
    sesion: Session, obra: models.Proyecto, descripcion: str, unidad: str
) -> tuple[Clave, models.Presupuesto]:
    """La clave del material en la procura de la obra y la versión explotada; `NoExiste` si la
    versión no lo pide."""
    clave = (descripcion.strip(), unidad.strip())
    fila = _linea_base(sesion, obra)
    version = (
        version_vigente(sesion, obra.nombre)
        if fila is None
        else sesion.get(models.Presupuesto, fila.presupuesto_id)
    )
    if version is None or all(linea.clave != clave for linea in _lineas(sesion, version)):
        raise NoExiste(f"«{clave[0]}» no es un material de la obra «{obra.nombre}».")
    return clave, version


def _positivo(texto: str, que: str) -> Decimal | None:
    if not texto.strip():
        return None
    valor = cifra_escrita(texto)
    if valor <= 0:
        raise ReglaDeProcura(f"{que} debe ser mayor que cero.")
    return valor


def _codigo_del_insumo(sesion: Session, version: models.Presupuesto, clave: Clave) -> str | None:
    """El código del insumo del catálogo de ese material: el de su línea en la versión o, si la
    línea no lo guardó, el primer material del catálogo con esa descripción y unidad."""
    insumo_id = next(
        (
            linea.insumo_id
            for linea in _lineas(sesion, version)
            if linea.clave == clave and linea.insumo_id is not None
        ),
        None,
    )
    if insumo_id is None:
        unidad = (
            models.Insumo.unidad.is_(None) if not clave[1] else models.Insumo.unidad == clave[1]
        )
        insumo_id = sesion.scalar(
            select(models.Insumo.id)
            .where(models.Insumo.tipo == _MATERIAL, models.Insumo.descripcion == clave[0], unidad)
            .order_by(models.Insumo.id)
            .limit(1)
        )
    insumo = None if insumo_id is None else sesion.get(models.Insumo, insumo_id)
    return None if insumo is None else insumo.codigo


def registrar_compra(
    sesion: Session,
    proyecto: str,
    *,
    descripcion: str,
    unidad: str,
    evento: str,
    fecha: date,
    cantidad: str = "",
    precio: str = "",
    responsable: str,
    ahora: datetime,
) -> None:
    """Anota que un material de la obra se pidió o se recibió el `fecha`.

    `cantidad` y `precio` son opcionales, como los tecleó la persona (`CifraInvalida` si no siguen
    la regla; `ReglaDeProcura` si no son mayores que cero). El precio va en la moneda de la carpeta
    (`CarpetaSinMoneda` si no la tiene); el de una recepción se anota además como observación de
    mercado de compra del insumo. `NoExiste` si la obra no existe o su procura no pide ese
    material; `ReglaDeProcura` si la fecha es posterior a `ahora`. No confirma."""
    if evento not in EVENTOS:
        raise ValueError(f"evento {evento!r}; se espera pedida o recibida")
    responsable = _responsable(responsable)
    obra = _obra(sesion, proyecto)
    clave, version = _material(sesion, obra, descripcion, unidad)
    if fecha > ahora.date():
        raise ReglaDeProcura("La fecha de la compra no puede ser posterior a hoy.")
    valor_cantidad = _positivo(cantidad, "La cantidad")
    valor_precio = _positivo(precio, "El precio")
    moneda = None
    if valor_precio is not None:
        moneda = moneda_de_la_carpeta(sesion, ahora.date())
        if moneda is None:
            raise CarpetaSinMoneda(MENSAJE_SIN_MONEDA)
    sesion.add(
        CompraDeInsumo(
            proyecto_id=obra.id,
            descripcion_insumo=clave[0],
            unidad=clave[1],
            evento=evento,
            fecha=fecha,
            cantidad=valor_cantidad,
            precio=valor_precio,
            moneda=moneda,
            responsable=responsable,
            fecha_hora=ahora,
        )
    )
    sesion.flush()
    if evento != "recibida" or valor_precio is None:
        return
    codigo = _codigo_del_insumo(sesion, version, clave)
    if codigo is None:
        return
    registrar_observacion(
        sesion,
        lado="compra",
        codigo=codigo,
        fuente_tipo="compra",
        fuente=f"Compra recibida en la obra {obra.nombre}"[:_LARGO_FUENTE],
        fecha=fecha,
        precio=precio,
        nota="",
        responsable=responsable,
        ahora=ahora,
    )


def fijar_plazo(
    sesion: Session, proyecto: str, *, descripcion: str, unidad: str, dias: str
) -> None:
    """Fija el plazo de entrega (días hábiles, tecleado: un entero de 0 a 365) de un material de la
    obra; reemplaza el anterior. `ReglaDeProcura` con `MENSAJE_PLAZO` si no es un entero de ese
    rango; `NoExiste` como en `registrar_compra`. No confirma."""
    try:
        valor = cifra_escrita(dias)
    except CifraInvalida:
        raise ReglaDeProcura(MENSAJE_PLAZO) from None
    if valor != valor.to_integral_value() or not 0 <= valor <= PLAZO_MAXIMO:
        raise ReglaDeProcura(MENSAJE_PLAZO)
    obra = _obra(sesion, proyecto)
    clave, _ = _material(sesion, obra, descripcion, unidad)
    fila = sesion.get(PlazoDeEntrega, (obra.id, *clave))
    if fila is None:
        sesion.add(
            PlazoDeEntrega(
                proyecto_id=obra.id, descripcion_insumo=clave[0], unidad=clave[1], dias=int(valor)
            )
        )
    else:
        fila.dias = int(valor)
    sesion.flush()


# --- pendientes de la mesa ----------------------------------------------------------------------


def pendientes_de_compras(sesion: Session, hoy: date) -> list[Pendiente]:
    """Fuente «compras» de la mesa: por obra con línea base, las alertas de su procura con
    `corte = hoy`, con su texto tal cual y la acción «Ver la procura» (Control de obra)."""
    # `aplicacion.mesa` registra esta fuente en `FUENTES`: importarla arriba sería circular.
    from aplicacion.mesa import Siguiente, pendiente

    accion = Siguiente(*VER_LA_PROCURA)
    salida = []
    for fila in proyectos_del_caso(sesion):
        obra = sesion.get(models.Proyecto, fila.id)
        if obra is None or _linea_base(sesion, obra) is None:
            continue
        leida = _procura_de(sesion, obra)
        for alerta in alertas_de_compra(leida.necesidades, hoy, leida.feriados):
            salida.append(pendiente(fila, alerta.texto, accion))
    return salida
