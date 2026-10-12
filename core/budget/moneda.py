"""SL-E1: moneda del proyecto y conversión de una versión (RF-64; spec S1 §5.3). La versión
convertida nace por `guardar_presupuesto`, el único embudo (M §3.2). No hace `commit`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar, _parametros_de
from core.budget.edicion import _exigir_codigo_libre, _exigir_respaldo, version_vigente
from core.budget.instantanea import composiciones_revaloradas, plan_de_version
from core.budget.persistencia import (
    _cargar_externos,
    _cargar_pendientes,
    cargar_presupuesto,
    guardar_presupuesto,
    moneda_declarada,
)
from core.budget.presupuesto import (
    CODIGO_ATIPICO,
    MONEDA_POR_DEFECTO,
    _declarar_externos,
    elaborar,
    exigir_composiciones,
)
from core.catalog import Catalogo
from core.catalog.moneda import TasaDeclarada, convertir, convertir_lista, exigir_moneda
from core.contracts.verificacion import ReglaVerificacion
from core.verification import REGLAS


def moneda_del_proyecto(session: Session, proyecto: models.Proyecto) -> str:
    declarada = moneda_declarada(session, proyecto.id)
    if declarada is not None:
        return declarada
    vigente = version_vigente(session, proyecto.nombre)
    return vigente.moneda if vigente is not None else MONEDA_POR_DEFECTO


def declarar_moneda(
    session: Session,
    proyecto: models.Proyecto,
    moneda: str,
    *,
    responsable: str,
    fuente: str = "al crear el proyecto (UC-01 paso 1)",
    ahora: datetime | None = None,
) -> models.MonedaProyecto:
    """UC-01 paso 1: la moneda elegida al crear el proyecto; con versiones, `convertir_version`."""
    if session.scalar(select(func.count()).select_from(models.Presupuesto)
                      .where(models.Presupuesto.proyecto_id == proyecto.id)):
        raise ValueError("el proyecto ya tiene versiones: cambiar su moneda es convertir_version")
    fila = models.MonedaProyecto(proyecto_id=proyecto.id, moneda=exigir_moneda(moneda),
                                 desde=ahora or datetime.now(), responsable=responsable.strip(),
                                 fuente=fuente)
    session.add(fila)
    session.flush()
    return fila


def convertir_version(
    session: Session, proyecto_nombre: str, codigo: str, codigo_nuevo: str, moneda: str,
    tasa: TasaDeclarada, *, fuente: str, responsable: str, catalogo: Catalogo,
    reglas: Sequence[ReglaVerificacion] = REGLAS, ahora: datetime | None = None,
) -> models.Presupuesto:
    """Versión nueva (motivo `conversion`) con lista derivada, líneas y bono convertidos y el plan
    conservado; fila de `moneda_proyecto` y `RegistroCambio` (objeto `moneda`, fuente = la tasa)."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    moneda = exigir_moneda(moneda)
    origen = _buscar(session, proyecto_nombre, codigo)
    if origen.moneda == moneda:
        raise ValueError(f"la version {codigo} ya esta en {moneda}")
    _exigir_codigo_libre(session, origen.proyecto_id, codigo_nuevo)
    anterior = cargar_presupuesto(session, proyecto_nombre, codigo, catalogo)
    lista = convertir_lista(session, origen.lista_precios, moneda, tasa,
                            nombre=f"{origen.lista_precios.nombre} en {moneda} ({codigo_nuevo})",
                            proyecto=origen.proyecto)
    items = [p.item for p in anterior.partidas]
    composiciones = composiciones_revaloradas(
        session, origen, catalogo, lista, list(dict.fromkeys(i.codigo_partida for i in items)),
        precio_sin_insumo=lambda p: convertir(p, origen.moneda, moneda, tasa.valor))
    exigir_composiciones(items, composiciones)
    parametros = replace(_parametros_de(origen), bono_alimentacion=convertir(
        origen.bono_alimentacion, origen.moneda, moneda, tasa.valor))
    plan = plan_de_version(session, origen)
    nuevo = elaborar([*items, *_cargar_pendientes(session, origen)], composiciones, parametros,
                     codigo=codigo_nuevo, fecha=origen.fecha, moneda=moneda, plan=plan,
                     reglas=tuple(reglas))
    externos = _cargar_externos(session, origen, tuple(reglas), sin=(CODIGO_ATIPICO,))
    nuevo = replace(nuevo, informe=_declarar_externos(nuevo.informe, externos))
    version = guardar_presupuesto(session, nuevo.presupuesto, nuevo.informe,
                                  proyecto=origen.proyecto, lista=lista, parametros=parametros,
                                  pendientes=nuevo.pendientes, plan=plan, version_origen=origen,
                                  motivo="conversion")
    momento = ahora or datetime.now()
    session.add(models.MonedaProyecto(proyecto_id=origen.proyecto_id, moneda=moneda, desde=momento,
                                      version_id=version.id, responsable=responsable,
                                      fuente=fuente))
    session.add(models.RegistroCambio(
        proyecto_id=origen.proyecto_id, version_origen_id=origen.id,
        version_resultante_id=version.id, objeto="moneda", clave=proyecto_nombre, campo="moneda",
        valor_anterior=origen.moneda, valor_nuevo=moneda, fuente=tasa.fuente,
        responsable=responsable, fecha_hora=momento))
    session.flush()
    return version
