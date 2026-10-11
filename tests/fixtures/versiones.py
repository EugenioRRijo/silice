"""Ayudantes de las pruebas de versiones (SF3): la 001 de la linea base y una edicion de su APU.

Unica copia de como se elabora, se guarda y se edita la linea base en las pruebas de SF-E2, SF-E6
y SF-E7. Nada escribe en `data/`: todo ocurre en la sesion de prueba.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from sqlalchemy import select

from core import models
from core.budget import ResultadoElaboracion, elaborar, guardar_presupuesto, plan_secuencial
from core.budget.edicion import CambioEditado
from core.catalog import Catalogo
from core.contracts.apu import ComposicionAPU
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import items_auditados

CEMENTO = "Cemento Portland"
CODIGO_CONCRETO = linea_base.APU_CONCRETO.codigo_partida
CAMBIO_CEMENTO = CambioEditado(
    objeto="apu",
    clave=f"{CODIGO_CONCRETO}|{CEMENTO}",
    campo="cantidad",
    valor_anterior="7.5",
    valor_nuevo="9",
)
FUENTE = "memoria de calculo rev. B, hoja 3"
RESPONSABLE = "Ing. Prueba"


def elaborar_001(sesion, codigo=linea_base.CODIGO_PRESUPUESTO, plan=plan_secuencial):
    catalogo = Catalogo(sesion)
    return elaborar(
        items_auditados(),
        catalogo.composiciones(
            list(linea_base.CODIGOS_LINEA_BASE), fecha=linea_base.FECHA_LINEA_BASE
        ),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan,
    )


def guardar_001(sesion, proyecto, resultado: ResultadoElaboracion, **opciones):
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=Catalogo(sesion).lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
        pendientes=resultado.pendientes,
        **opciones,
    )


def con_cemento(composicion: ComposicionAPU, cantidad: str = "9") -> ComposicionAPU:
    """El APU del concreto con otra cantidad de cemento por m3 (una edicion de la hoja)."""
    return replace(
        composicion,
        materiales=tuple(
            replace(m, cantidad=Decimal(cantidad)) if m.descripcion == CEMENTO else m
            for m in composicion.materiales
        ),
    )


def elaborar_editada(sesion, composiciones, codigo: str, plan=plan_secuencial):
    """La linea base elaborada con `composiciones` (ya editadas) bajo el codigo `codigo`."""
    return elaborar(
        items_auditados(),
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan,
    )


def editar_apu_en_la_hoja(sesion, catalogo=None, codigo=linea_base.CODIGO_PRESUPUESTO):
    """Abre `codigo` en la hoja, sube el cemento del concreto en su copia y guarda la version
    siguiente. Devuelve el total exacto de la version nueva (el catalogo no cambia)."""
    from ui import hoja

    catalogo = catalogo or Catalogo(sesion)
    nombre = sesion.scalars(select(models.Proyecto.nombre)).one()
    abierta = hoja.abrir_version(sesion, catalogo, nombre, codigo)
    composiciones = dict(abierta.borrador.composiciones)
    composiciones[CODIGO_CONCRETO] = con_cemento(composiciones[CODIGO_CONCRETO])
    guardada = hoja.guardar_version(
        sesion,
        catalogo,
        abierta,
        replace(abierta.borrador, composiciones=composiciones),
        fuente=FUENTE,
        responsable=RESPONSABLE,
    )
    return guardada
