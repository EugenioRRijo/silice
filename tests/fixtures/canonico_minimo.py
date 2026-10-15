"""La versión mínima del vector de huella (S3 §13.1): una partida, tres insumos, un renglón.

`sembrar_minimo(sesion)` guarda la versión `001` del proyecto «MIN-001» con lo que describe a mano
`tests/fixtures/canonico/ejemplo_v1.py`. Los números están elegidos para que cada monto salga
exacto: RELLENO de 20 m3 con rendimiento 8 y los parámetros de la línea base.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

FECHA = date(2026, 11, 1)
PARAMETROS = ParametrosCosto()
USUARIO = "Ana Pérez <ana>"
AHORA = datetime(2026, 11, 1, 10, 0, 0)

RELLENO = ComposicionAPU(
    codigo_partida="MIN-001",
    descripcion="Relleno de prueba",
    unidad="m3",
    rendimiento=Decimal("8"),
    materiales=(LineaMaterial("Arena", "m3", Decimal("1.00"), Decimal("14.00")),),
    equipos=(LineaEquipo("Compactadora", Decimal("1"), Decimal("71.00"), Decimal("0.10")),),
    mano_obra=(LineaManoObra("Obrero", Decimal("2"), Decimal("10.25")),),
)
ITEM = ItemComputo(
    codigo_partida="MIN-001",
    descripcion="Relleno de prueba",
    unidad="m3",
    cantidad=Decimal("20"),
    origen_id="FILA-1",
    origen_tipo=OrigenTipo.TABULAR,
    dominio=Dominio.CIVIL,
)


def _elaborar(codigo: str, cantidad: str):
    item = ItemComputo(
        codigo_partida="MIN-001",
        descripcion="Relleno de prueba",
        unidad="m3",
        cantidad=Decimal(cantidad),
        origen_id="FILA-1",
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )
    return elaborar(
        [item],
        {"MIN-001": RELLENO},
        PARAMETROS,
        codigo=codigo,
        fecha=FECHA,
        moneda="USD",
        plan=plan_secuencial,
    )


def guardar_otra(
    sesion,
    proyecto,
    lista,
    codigo: str,
    cantidad: str = "20",
    usuario: str | None = USUARIO,
    **opciones,
):
    """Otra versión del mismo relleno por el embudo; `opciones` van tal cual a
    `guardar_presupuesto` (`version_origen`, `motivo`, `anexos_de`...)."""
    resultado = _elaborar(codigo, cantidad)
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=lista,
        parametros=PARAMETROS,
        pendientes=resultado.pendientes,
        usuario=usuario,
        **opciones,
    )


def sembrar_minimo(sesion, usuario: str | None = USUARIO, **opciones):
    """Devuelve `(proyecto, version, lista)`; la sesión queda con la transacción abierta.
    `opciones` va al embudo (p. ej. `anexos_de=`)."""
    lista = models.ListaPrecios(
        nombre="Lista de prueba", moneda="USD", fecha_vigencia=FECHA, origen="prueba"
    )
    sesion.add(lista)
    sesion.flush()
    Catalogo(sesion).cargar_composicion(RELLENO, lista, Dominio.CIVIL, FECHA, "prueba")
    proyecto = crear_proyecto(sesion, "MIN-001", dominio=Dominio.CIVIL)
    version = guardar_otra(sesion, proyecto, lista, "001", usuario=usuario, **opciones)
    return proyecto, version, lista


def registro(proyecto, origen, resultante, campo="cantidad", responsable=USUARIO):
    """Un `RegistroCambio` de la versión `resultante`, como los que agregan edición y cotización."""
    return models.RegistroCambio(
        proyecto_id=proyecto.id,
        version_origen_id=origen.id if origen else None,
        version_resultante_id=resultante.id,
        objeto="apu",
        clave="MIN-001|Arena",
        campo=campo,
        valor_anterior="1.00",
        valor_nuevo="1.50",
        fuente="memoria rev. B",
        responsable=responsable,
        fecha_hora=AHORA,
    )
