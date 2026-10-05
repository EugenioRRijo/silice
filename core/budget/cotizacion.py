"""SF‑E7: cotizar un insumo para un proyecto y retirar la cotización (RF‑56, DA‑SF‑9, spec §9.6).

Una cotización (proveedor, número y fecha) crea una **lista de precios del proyecto**: copia de la
lista base con ese insumo a su precio cotizado, que la versión nueva referencia explícitamente. No
cambia ningún otro proyecto ni la lista global. La versión resultante **conserva el plan y la
curva** de la versión de origen (el reparto se lee de su instantánea, SF‑E6), sus composiciones
congeladas con el precio nuevo, sus pendientes y los hallazgos de reglas externas, y declara su
`version_origen` (motivo `cotizacion`) y un `RegistroCambio` (SF‑E2). Una carga global posterior
por UC‑02 no pisa la cotización (`actualizar_precios` la repone sobre la lista base nueva) hasta que
`retirar_cotizacion` la quita, también con su registro. Ninguna función confirma la transacción.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.edicion import _exigir_codigo_libre, _exigir_respaldo
from core.budget.instantanea import composiciones_revaloradas, plan_de_version
from core.budget.persistencia import (
    _buscar,
    _cargar_externos,
    _cargar_pendientes,
    _parametros_de,
    cargar_presupuesto,
    guardar_presupuesto,
)
from core.budget.presupuesto import _declarar_externos, elaborar, exigir_composiciones
from core.catalog import Catalogo
from core.catalog.origen import (
    Cotizado,
    cotizaciones_activas,
    crear_lista_de_proyecto,
    lista_base,
)
from core.contracts.verificacion import ReglaVerificacion
from core.verification import REGLAS

__all__ = ["cotizaciones_de_version", "cotizar_insumo", "retirar_cotizacion"]


def cotizaciones_de_version(
    session: Session, modelo: models.Presupuesto
) -> list[models.Cotizacion]:
    """Las cotizaciones activas de la versión (vacío si se valoró con una lista global)."""
    return list(
        session.scalars(
            select(models.Cotizacion)
            .where(models.Cotizacion.lista_id == modelo.lista_precios_id)
            .order_by(models.Cotizacion.id)
        )
    )


def _insumo(session: Session, insumo: models.Insumo | str) -> models.Insumo:
    if isinstance(insumo, models.Insumo):
        return insumo
    encontrado = session.scalars(
        select(models.Insumo).where(models.Insumo.codigo == insumo)
    ).one_or_none()
    if encontrado is None:
        raise ValueError(f"no hay ningun insumo con codigo {insumo!r}")
    return encontrado


def _precio_en(lista: models.ListaPrecios, insumo: models.Insumo) -> Decimal | None:
    return next((p.precio for p in lista.precios if p.insumo_id == insumo.id), None)


def _usa(session: Session, modelo: models.Presupuesto, insumo: models.Insumo) -> bool:
    """True si alguna línea de las composiciones de la versión (instantánea o, si falta, catálogo)
    es de ese insumo."""
    congeladas = set(
        session.scalars(
            select(models.ComposicionVersion.codigo_partida).where(
                models.ComposicionVersion.presupuesto_id == modelo.id
            )
        )
    )
    en_instantanea = session.scalar(
        select(models.LineaComposicionVersion.id)
        .join(models.ComposicionVersion)
        .where(
            models.ComposicionVersion.presupuesto_id == modelo.id,
            models.LineaComposicionVersion.insumo_id == insumo.id,
        )
        .limit(1)
    )
    if en_instantanea is not None:
        return True
    sin = [r.partida.id for r in modelo.partidas if r.partida.codigo not in congeladas]
    return bool(sin) and (
        session.scalar(
            select(models.ComposicionAPU.id)
            .where(
                models.ComposicionAPU.partida_id.in_(sin),
                models.ComposicionAPU.insumo_id == insumo.id,
            )
            .limit(1)
        )
        is not None
    )


def _guardar_version(
    session: Session,
    proyecto_nombre: str,
    codigo_origen: str,
    codigo_nuevo: str,
    catalogo: Catalogo,
    lista: models.ListaPrecios,
    reglas: Sequence[ReglaVerificacion],
) -> models.Presupuesto:
    """La versión `codigo_nuevo` valorada con `lista`: mismas cantidades, parámetros, pendientes,
    plan y curva; composiciones de la instantánea con los precios de `lista`; externos
    arrastrados."""
    reglas = tuple(reglas)
    origen = _buscar(session, proyecto_nombre, codigo_origen)
    anterior = cargar_presupuesto(session, proyecto_nombre, codigo_origen, catalogo)
    items = [partida.item for partida in anterior.partidas]
    composiciones = composiciones_revaloradas(
        session,
        origen,
        catalogo,
        lista,
        list(dict.fromkeys(item.codigo_partida for item in items)),
    )
    exigir_composiciones(items, composiciones)
    parametros = _parametros_de(origen)
    plan = plan_de_version(session, origen)
    nuevo = elaborar(
        [*items, *_cargar_pendientes(session, origen)],
        composiciones,
        parametros,
        codigo=codigo_nuevo,
        fecha=origen.fecha,
        moneda=anterior.moneda,
        plan=plan,
        reglas=reglas,
    )
    nuevo = replace(
        nuevo,
        informe=_declarar_externos(nuevo.informe, _cargar_externos(session, origen, reglas)),
    )
    return guardar_presupuesto(
        session,
        nuevo.presupuesto,
        nuevo.informe,
        proyecto=origen.proyecto,
        lista=lista,
        parametros=parametros,
        pendientes=nuevo.pendientes,
        plan=plan,
        version_origen=origen,
        motivo="cotizacion",
    )


def _registrar(
    session: Session,
    origen: models.Presupuesto,
    nueva: models.Presupuesto,
    insumo: models.Insumo,
    anterior: str,
    nuevo: str,
    fuente: str,
    responsable: str,
    ahora: datetime | None,
) -> None:
    session.add(
        models.RegistroCambio(
            proyecto_id=origen.proyecto_id,
            version_origen_id=origen.id,
            version_resultante_id=nueva.id,
            objeto="precio",
            clave=insumo.codigo,
            campo="cotizacion",
            valor_anterior=anterior,
            valor_nuevo=nuevo,
            fuente=fuente,
            responsable=responsable,
            fecha_hora=ahora or datetime.now(),
        )
    )
    session.flush()


def _nombre_de_lista(base: models.ListaPrecios, proyecto: models.Proyecto, codigo: str) -> str:
    return f"{base.nombre} + cotizaciones de {proyecto.nombre} ({codigo})"


def cotizar_insumo(
    session: Session,
    proyecto_nombre: str,
    codigo_origen: str,
    codigo_nuevo: str,
    catalogo: Catalogo,
    *,
    insumo: models.Insumo | str,
    precio: Decimal,
    proveedor: str,
    numero: str,
    fecha: date,
    responsable: str,
    fuente: str = "",
    ahora: datetime | None = None,
    reglas: Sequence[ReglaVerificacion] = REGLAS,
) -> models.Presupuesto:
    """Cotiza `insumo` a `precio` para el proyecto: crea su lista de proyecto y la versión
    `codigo_nuevo` que la referencia (RF‑56).

    `proveedor`, `numero` y `responsable` son obligatorios; `fuente` agrega el respaldo (evidencia
    del protocolo de levantamiento de precios) a la que el sistema arma con el proveedor, el número
    y la fecha. `ValueError`, sin dejar filas, si falta algo, si el precio es negativo o ya es el
    de la lista de la versión, si la versión no usa el insumo o si el código de versión existe.
    Una cotización previa del mismo insumo se reemplaza; las de otros insumos se conservan.
    """
    proveedor, numero = proveedor.strip(), numero.strip()
    if not proveedor:
        raise ValueError("el proveedor de la cotizacion es obligatorio")
    if not numero:
        raise ValueError("el numero de la cotizacion es obligatorio")
    respaldo = f"Cotizacion {numero} de {proveedor} ({fecha.isoformat()})"
    fuente, responsable = _exigir_respaldo(f"{respaldo}. {fuente}".strip(), responsable)
    if not isinstance(precio, Decimal) or precio < 0:
        raise ValueError(f"el precio cotizado debe ser un Decimal no negativo, no {precio!r}")
    origen = _buscar(session, proyecto_nombre, codigo_origen)
    insumo = _insumo(session, insumo)
    if not _usa(session, origen, insumo):
        raise ValueError(f"la version {codigo_origen!r} no usa el insumo {insumo.codigo}")
    actual = _precio_en(origen.lista_precios, insumo)
    if actual is not None and precio == actual:
        raise ValueError(f"el insumo {insumo.codigo} ya vale {precio} en la lista de la version")
    _exigir_codigo_libre(session, origen.proyecto_id, codigo_nuevo)

    base = lista_base(session, origen.lista_precios)
    previas = {c.insumo_id: c for c in cotizaciones_activas(session, origen.lista_precios)}
    en_base = _precio_en(base, insumo)
    previas[insumo.id] = Cotizado(insumo.id, precio, en_base, proveedor, numero, fecha)
    lista = crear_lista_de_proyecto(
        session,
        origen.proyecto,
        base,
        list(previas.values()),
        _nombre_de_lista(base, origen.proyecto, codigo_nuevo),
    )
    nueva = _guardar_version(
        session, proyecto_nombre, codigo_origen, codigo_nuevo, catalogo, lista, reglas
    )
    _registrar(
        session,
        origen,
        nueva,
        insumo,
        "" if actual is None else str(actual),
        str(precio),
        fuente,
        responsable,
        ahora,
    )
    return nueva


def retirar_cotizacion(
    session: Session,
    proyecto_nombre: str,
    codigo_origen: str,
    codigo_nuevo: str,
    catalogo: Catalogo,
    *,
    insumo: models.Insumo | str,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
    reglas: Sequence[ReglaVerificacion] = REGLAS,
) -> models.Presupuesto:
    """Retira la cotización de `insumo`: la versión `codigo_nuevo` vuelve al precio de la lista
    base para ese insumo (conservando las demás cotizaciones; sin ninguna usa la lista base) y
    deja su `RegistroCambio` con la fuente y el responsable. `ValueError` si la versión no tiene
    esa cotización. No confirma."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    origen = _buscar(session, proyecto_nombre, codigo_origen)
    insumo = _insumo(session, insumo)
    activas = {c.insumo_id: c for c in cotizaciones_activas(session, origen.lista_precios)}
    if insumo.id not in activas:
        raise ValueError(
            f"la version {codigo_origen!r} no tiene cotizacion del insumo {insumo.codigo}"
        )
    _exigir_codigo_libre(session, origen.proyecto_id, codigo_nuevo)
    cotizada = activas.pop(insumo.id)
    base = lista_base(session, origen.lista_precios)
    lista = crear_lista_de_proyecto(
        session,
        origen.proyecto,
        base,
        list(activas.values()),
        _nombre_de_lista(base, origen.proyecto, codigo_nuevo),
    )
    nueva = _guardar_version(
        session, proyecto_nombre, codigo_origen, codigo_nuevo, catalogo, lista, reglas
    )
    vuelve = _precio_en(base, insumo)
    _registrar(
        session,
        origen,
        nueva,
        insumo,
        str(cotizada.precio),
        "" if vuelve is None else str(vuelve),
        fuente,
        responsable,
        ahora,
    )
    return nueva
