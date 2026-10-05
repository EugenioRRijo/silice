"""SF‑E6: la instantánea de composiciones, rendimientos y plan de cada versión.

Cada versión que se guarda congela las líneas de APU con que se valoró cada partida (con el
rendimiento de esa versión) y el reparto de su plan de trabajo. Toda recarga, la verificación del
precio unitario, la revaloración por UC‑02 y los escenarios toman la composición **por código de
partida** de aquí cuando existe y del catálogo solo cuando no (versiones anteriores a SF‑E6, o
partidas que `asegurar_instantanea` no pudo congelar). El contrato `ComposicionAPU` no cambia: la
instantánea guarda sus líneas tal cual.

Este módulo es el único que lee o escribe las tablas `composicion_version`,
`linea_composicion_version` y `plan_version`. No hace `commit`.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar, _parametros_de
from core.budget.curva import PeriodoPlan
from core.catalog import Catalogo
from core.catalog.errores import CatalogoIncompleto
from core.catalog.mapeo import LineaCatalogo, lineas_de
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    ParametrosCosto,
)
from core.contracts.presupuesto import Presupuesto
from core.costing import calcular_apu
from core.verification.directivas import codigos_en_etiqueta

__all__ = [
    "ResultadoInstantanea",
    "asegurar_instantanea",
    "composiciones_de_presupuesto",
    "composiciones_de_version",
    "composiciones_revaloradas",
    "congelar",
    "partidas_por_insumo",
    "plan_de_version",
    "tiene_instantanea",
]

#: Diferencia máxima entre el PU que da una composición y el del renglón guardado.
TOLERANCIA_PU = Decimal("0.000001")

_SUFIJO_CODIGOS = re.compile(r"\s*\[[^\[\]]*\]\s*$")


@dataclass(frozen=True, slots=True)
class ResultadoInstantanea:
    """Qué hizo `asegurar_instantanea`: partidas congeladas ahora y partidas que quedan sin
    composición vigente (solo lectura en la hoja, UC‑15e)."""

    creadas: tuple[str, ...] = ()
    sin_composicion: tuple[str, ...] = ()


# ---------------------------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------------------------


def _filas(session: Session, modelo: models.Presupuesto) -> list[models.ComposicionVersion]:
    return list(
        session.scalars(
            select(models.ComposicionVersion)
            .where(models.ComposicionVersion.presupuesto_id == modelo.id)
            .order_by(models.ComposicionVersion.id)
        )
    )


def tiene_instantanea(session: Session, modelo: models.Presupuesto) -> bool:
    """True si la versión congeló la composición de al menos una partida."""
    return (
        session.scalar(
            select(models.ComposicionVersion.id)
            .where(models.ComposicionVersion.presupuesto_id == modelo.id)
            .limit(1)
        )
        is not None
    )


def _a_composicion(
    fila: models.ComposicionVersion,
    precio_de: Callable[[models.LineaComposicionVersion], Decimal] | None = None,
) -> ComposicionAPU:
    """El `ComposicionAPU` de una fila; `precio_de` sustituye el precio congelado de cada línea."""
    materiales: list[LineaMaterial] = []
    equipos: list[LineaEquipo] = []
    mano_obra: list[LineaManoObra] = []
    for linea in sorted(fila.lineas, key=lambda linea: linea.orden):
        precio = linea.precio if precio_de is None else precio_de(linea)
        if linea.tipo == models.TipoInsumo.MATERIAL:
            materiales.append(
                LineaMaterial(linea.descripcion, linea.unidad or "", linea.cantidad, precio)
            )
        elif linea.tipo == models.TipoInsumo.EQUIPO:
            equipos.append(
                LineaEquipo(linea.descripcion, linea.cantidad, precio, linea.depreciacion)
            )
        else:
            mano_obra.append(
                LineaManoObra(
                    linea.descripcion,
                    linea.cantidad,
                    precio,
                    ModalidadManoObra(linea.modalidad)
                    if linea.modalidad
                    else ModalidadManoObra.JORNAL,
                )
            )
    return ComposicionAPU(
        codigo_partida=fila.codigo_partida,
        descripcion=fila.descripcion,
        unidad=fila.unidad,
        rendimiento=fila.rendimiento,
        materiales=tuple(materiales),
        equipos=tuple(equipos),
        mano_obra=tuple(mano_obra),
    )


def composiciones_de_version(
    session: Session, modelo: models.Presupuesto
) -> dict[str, ComposicionAPU]:
    """Las composiciones congeladas de la versión, por código de partida (vacío si no hay)."""
    return {fila.codigo_partida: _a_composicion(fila) for fila in _filas(session, modelo)}


def _codigos_de(modelo: models.Presupuesto) -> list[str]:
    return list(dict.fromkeys(renglon.partida.codigo for renglon in modelo.partidas))


def composiciones_de_presupuesto(
    session: Session, proyecto_nombre: str, codigo: str, catalogo: Catalogo
) -> dict[str, ComposicionAPU]:
    """Las composiciones con que se valoró una versión: la instantánea y, solo para las partidas
    que no la tienen, el catálogo con la lista y la fecha de la versión. Es lo que usan los
    escenarios y la hoja (SF‑E6)."""
    modelo = _buscar(session, proyecto_nombre, codigo)
    congeladas = composiciones_de_version(session, modelo)
    return {
        partida: congeladas.get(partida)
        or catalogo.composicion(partida, fecha=modelo.fecha, lista=modelo.lista_precios)
        for partida in _codigos_de(modelo)
    }


def composiciones_revaloradas(
    session: Session,
    modelo: models.Presupuesto,
    catalogo: Catalogo,
    lista: models.ListaPrecios,
    codigos: Sequence[str],
) -> dict[str, ComposicionAPU]:
    """UC‑02: las líneas de la instantánea con los precios de `lista` (por insumo).

    Una línea sin insumo conserva su precio; un insumo sin precio en `lista` es
    `CatalogoIncompleto`. Una partida sin instantánea se reconstruye del catálogo con `lista`.
    """
    filas = {fila.codigo_partida: fila for fila in _filas(session, modelo)}
    precios = {precio.insumo_id: precio.precio for precio in lista.precios}

    def precio_de(linea: models.LineaComposicionVersion) -> Decimal:
        if linea.insumo_id is None:
            return linea.precio
        precio = precios.get(linea.insumo_id)
        if precio is None:
            raise CatalogoIncompleto(
                f"el insumo {linea.descripcion} no tiene precio en la lista '{lista.nombre}'; "
                f"no se puede valorar la partida {linea.composicion.codigo_partida}"
            )
        return precio

    return {
        codigo: (
            _a_composicion(filas[codigo], precio_de)
            if codigo in filas
            else catalogo.composicion(codigo, fecha=lista.fecha_vigencia, lista=lista)
        )
        for codigo in codigos
    }


def partidas_por_insumo(
    session: Session, version_id: int, insumos: Sequence[int], codigos: Sequence[str]
) -> dict[int, list[models.Partida]]:
    """Qué partidas llevan cada insumo: según la instantánea de la versión y, para las que no la
    tienen, según la composición del catálogo. Cada partida aparece una vez por insumo."""
    congeladas = set(
        session.scalars(
            select(models.ComposicionVersion.codigo_partida).where(
                models.ComposicionVersion.presupuesto_id == version_id
            )
        )
    )
    de_instantanea = [c for c in codigos if c in congeladas]
    de_catalogo = [c for c in codigos if c not in congeladas]
    filas: list[tuple[int, models.Partida]] = []
    if de_instantanea:
        filas += [
            (insumo_id, partida)
            for insumo_id, partida in session.execute(
                select(models.LineaComposicionVersion.insumo_id, models.Partida)
                .join(
                    models.ComposicionVersion,
                    models.ComposicionVersion.id == models.LineaComposicionVersion.composicion_id,
                )
                .join(
                    models.Partida,
                    models.Partida.codigo == models.ComposicionVersion.codigo_partida,
                )
                .where(
                    models.ComposicionVersion.presupuesto_id == version_id,
                    models.LineaComposicionVersion.insumo_id.in_(insumos),
                    models.ComposicionVersion.codigo_partida.in_(de_instantanea),
                )
            ).all()
        ]
    if de_catalogo:
        filas += [
            (insumo_id, partida)
            for insumo_id, partida in session.execute(
                select(models.ComposicionAPU.insumo_id, models.Partida)
                .join(models.Partida, models.Partida.id == models.ComposicionAPU.partida_id)
                .where(
                    models.ComposicionAPU.insumo_id.in_(insumos),
                    models.Partida.codigo.in_(de_catalogo),
                )
            ).all()
        ]
    filas.sort(key=lambda fila: fila[1].codigo)
    por_insumo: dict[int, list[models.Partida]] = {}
    for insumo_id, partida in filas:
        partidas = por_insumo.setdefault(insumo_id, [])
        if all(registrada.id != partida.id for registrada in partidas):
            partidas.append(partida)
    return por_insumo


# ---------------------------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------------------------


def _resolver_insumos(
    session: Session, lineas: Sequence[LineaCatalogo], lista: models.ListaPrecios
) -> list[int | None]:
    """El insumo del catálogo de cada línea: entre los de su tipo y descripción, el que tiene en la
    lista el precio de la línea (hay homónimos con precio distinto, modelo_datos §6) y, si
    ninguno coincide, el primero que la lista valora. `None` si no hay ninguno."""
    precios = {precio.insumo_id: precio.precio for precio in lista.precios}
    candidatos: dict[tuple[str, str], list[int]] = {}
    resueltos: list[int | None] = []
    for linea in lineas:
        clave = (linea.tipo.value, linea.descripcion)
        if clave not in candidatos:
            candidatos[clave] = list(
                session.scalars(
                    select(models.Insumo.id)
                    .where(
                        models.Insumo.tipo == clave[0], models.Insumo.descripcion == clave[1]
                    )
                    .order_by(models.Insumo.id)
                )
            )
        ids = candidatos[clave]
        exacto = next((i for i in ids if precios.get(i) == linea.precio), None)
        resueltos.append(exacto or next((i for i in ids if i in precios), None))
    return resueltos


def _insumos_heredados(
    session: Session,
    origen: models.Presupuesto,
    composicion: ComposicionAPU,
    lineas: Sequence[LineaCatalogo],
) -> list[int | None] | None:
    """El `insumo_id` de cada línea tomado de la instantánea de `origen` (SF3 R‑7), o `None` si no
    se puede heredar (la versión de origen no congeló la partida o la estructura de líneas cambió).

    Regla: una línea que sigue en la misma posición con el mismo tipo y descripción hereda el
    `insumo_id` de origen **si conserva su precio**; si el precio cambió es un precio manual y
    queda sin insumo (`None`), para que una revaloración posterior (UC‑02) no lo pise con la lista.
    """
    fila = session.scalars(
        select(models.ComposicionVersion).where(
            models.ComposicionVersion.presupuesto_id == origen.id,
            models.ComposicionVersion.codigo_partida == composicion.codigo_partida,
        )
    ).first()
    if fila is None:
        return None
    anteriores = sorted(fila.lineas, key=lambda linea: linea.orden)
    if len(anteriores) != len(lineas) or any(
        anterior.tipo != linea.tipo.value or anterior.descripcion != linea.descripcion
        for anterior, linea in zip(anteriores, lineas, strict=True)
    ):
        return None
    return [
        anterior.insumo_id if anterior.precio == linea.precio else None
        for anterior, linea in zip(anteriores, lineas, strict=True)
    ]


def _escribir_composicion(
    session: Session,
    modelo: models.Presupuesto,
    composicion: ComposicionAPU,
    lista: models.ListaPrecios,
    origen: models.Presupuesto | None = None,
) -> None:
    lineas = lineas_de(composicion)
    insumos = (
        _insumos_heredados(session, origen, composicion, lineas) if origen is not None else None
    )
    if insumos is None:
        insumos = _resolver_insumos(session, lineas, lista)
    fila = models.ComposicionVersion(
        presupuesto_id=modelo.id,
        codigo_partida=composicion.codigo_partida,
        descripcion=composicion.descripcion,
        unidad=composicion.unidad,
        rendimiento=composicion.rendimiento,
    )
    for orden, (linea, insumo_id) in enumerate(zip(lineas, insumos, strict=True)):
        fila.lineas.append(
            models.LineaComposicionVersion(
                orden=orden,
                tipo=linea.tipo.value,
                insumo_id=insumo_id,
                descripcion=linea.descripcion,
                unidad=linea.unidad,
                cantidad=linea.cantidad,
                precio=linea.precio,
                depreciacion=linea.depreciacion,
                modalidad=linea.modalidad.value if linea.modalidad is not None else None,
            )
        )
    session.add(fila)


def _escribir_plan(
    session: Session, modelo: models.Presupuesto, plan: Sequence[PeriodoPlan]
) -> None:
    for periodo, (etiqueta, reparto) in enumerate(plan):
        if not reparto:
            session.add(
                models.PlanVersion(
                    presupuesto_id=modelo.id, periodo=periodo, etiqueta=etiqueta, orden=0
                )
            )
        for orden, (codigo, fraccion) in enumerate(reparto):
            session.add(
                models.PlanVersion(
                    presupuesto_id=modelo.id,
                    periodo=periodo,
                    etiqueta=etiqueta,
                    orden=orden,
                    codigo_partida=codigo,
                    fraccion=fraccion,
                )
            )


def _plan_inferido(periodos: Sequence[str], codigos: set[str]) -> list[PeriodoPlan] | None:
    """El plan que revela la curva cuando cada partida está en un único período (fracción 1).

    `periodos` son las etiquetas de la curva, con los códigos entre corchetes. Si alguna partida
    está en varios períodos, o en ninguno, el reparto no es inferible: `None` (no se inventa)."""
    if not periodos:
        return None
    citados = [codigos_en_etiqueta(etiqueta) for etiqueta in periodos]
    veces = Counter(codigo for grupo in citados for codigo in set(grupo))
    if set(veces) != codigos or any(cuenta != 1 for cuenta in veces.values()):
        return None
    return [
        (_SUFIJO_CODIGOS.sub("", etiqueta), tuple((codigo, Decimal(1)) for codigo in grupo))
        for etiqueta, grupo in zip(periodos, citados, strict=True)
    ]


def congelar(
    session: Session,
    modelo: models.Presupuesto,
    presupuesto: Presupuesto,
    lista: models.ListaPrecios,
    plan: Sequence[PeriodoPlan] | None = None,
    origen: models.Presupuesto | None = None,
) -> None:
    """Congela en `modelo` (ya con `id`) el `apu` de cada código de partida distinto del
    presupuesto y su plan: el dado o, sin él, el inferible de la curva.

    Con `origen`, el insumo de cada línea se hereda de la instantánea de esa versión (restaurar,
    editar) en vez de re‑resolverse por tipo, descripción y precio (`_insumos_heredados`)."""
    vistos: set[str] = set()
    for partida in presupuesto.partidas:
        if partida.apu.codigo_partida not in vistos:
            vistos.add(partida.apu.codigo_partida)
            _escribir_composicion(session, modelo, partida.apu, lista, origen)
    if plan is None:
        plan = _plan_inferido(
            [punto.periodo for punto in presupuesto.curva],
            {partida.item.codigo_partida for partida in presupuesto.partidas},
        )
    if plan:
        _escribir_plan(session, modelo, plan)
    session.flush()


def plan_de_version(session: Session, modelo: models.Presupuesto) -> list[PeriodoPlan] | None:
    """El plan de trabajo congelado de la versión, o `None` si no se guardó ni era inferible."""
    filas = session.scalars(
        select(models.PlanVersion)
        .where(models.PlanVersion.presupuesto_id == modelo.id)
        .order_by(models.PlanVersion.periodo, models.PlanVersion.orden)
    ).all()
    if not filas:
        return None
    periodos: dict[int, tuple[str, list[tuple[str, Decimal]]]] = {}
    for fila in filas:
        _, reparto = periodos.setdefault(fila.periodo, (fila.etiqueta, []))
        if fila.codigo_partida is not None and fila.fraccion is not None:
            reparto.append((fila.codigo_partida, fila.fraccion))
    return [(etiqueta, tuple(reparto)) for etiqueta, reparto in periodos.values()]


def asegurar_instantanea(
    session: Session,
    proyecto_nombre: str,
    codigo: str,
    catalogo: Catalogo,
    parametros: ParametrosCosto | None = None,
    *,
    responsable: str = "sistema",
    ahora: datetime | None = None,
) -> ResultadoInstantanea:
    """UC‑15e: congela desde el catálogo vigente las partidas de la versión que no tienen
    instantánea, solo si el catálogo todavía reproduce su precio unitario.

    Las que no tienen composición en el catálogo, o cuyo PU ya no cuadra con el renglón guardado,
    quedan en `sin_composicion` (solo lectura). Idempotente: no toca lo ya congelado. También
    congela el plan si la versión no lo tiene y la curva lo revela. Si congeló algo, lo registra con
    un `RegistroCambio` (objeto `apu`, campo `instantanea`; UC‑15e). No hace `commit`.
    """
    modelo = _buscar(session, proyecto_nombre, codigo)
    parametros = parametros or _parametros_de(modelo)
    congeladas = {fila.codigo_partida for fila in _filas(session, modelo)}
    creadas: list[str] = []
    sin: list[str] = []
    for partida in _codigos_de(modelo):
        if partida in congeladas:
            continue
        try:
            composicion = catalogo.composicion(
                partida, fecha=modelo.fecha, lista=modelo.lista_precios
            )
        except (KeyError, CatalogoIncompleto):
            sin.append(partida)
            continue
        reconstruido = calcular_apu(composicion, parametros).precio_unitario
        if any(
            abs(reconstruido - renglon.precio_unitario) > TOLERANCIA_PU
            for renglon in modelo.partidas
            if renglon.partida.codigo == partida
        ):
            sin.append(partida)
            continue
        _escribir_composicion(session, modelo, composicion, modelo.lista_precios)
        creadas.append(partida)
    if creadas:
        session.add(
            models.RegistroCambio(
                proyecto_id=modelo.proyecto_id,
                version_origen_id=modelo.id,
                version_resultante_id=modelo.id,
                objeto="apu",
                clave=", ".join(creadas),
                campo="instantanea",
                valor_anterior="catalogo",
                valor_nuevo="instantanea",
                fuente=(
                    "al abrir la version se creo su instantanea de composiciones desde el "
                    "catalogo vigente (UC-15e)"
                ),
                responsable=responsable,
                fecha_hora=ahora or datetime.now(),
            )
        )
    session.flush()
    tiene_plan = (
        session.scalar(
            select(models.PlanVersion.id)
            .where(models.PlanVersion.presupuesto_id == modelo.id)
            .limit(1)
        )
        is not None
    )
    if not tiene_plan:
        plan = _plan_inferido(
            [punto.periodo for punto in modelo.curva], set(_codigos_de(modelo))
        )
        if plan:
            _escribir_plan(session, modelo, plan)
            session.flush()
    return ResultadoInstantanea(creadas=tuple(creadas), sin_composicion=tuple(sin))
