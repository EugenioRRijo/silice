"""Bases de prueba de la hoja (SF3): OF-001 con su espacio, TI-001 y la clinica, en SQLite temporal.

`plantilla_of001(ruta)` y `plantilla_ti001(ruta)` siembran una vez un archivo con el catalogo de
cada caso (una composicion por partida), su lista de precios y la version `001` guardada con su
instantanea; la de OF-001 guarda ademas su espacio `esp_*`. Las pruebas copian el archivo (barato)
y trabajan sobre la copia. Nada escribe en `data/`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select

from adapters.espacio import crear_esquema_espacio, guardar_espacio
from core import models
from core.budget import crear_proyecto, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts.dominio import Dominio
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.espacio_of001 import espacio_of001
from ui import hoja
from ui.entrega import con_anexos_de_cadena

NOMBRE_OF001 = "OF-001: oficina con baño, cocineta y puestos (caso de prueba)"
NOMBRE_TI001 = "TI-001: telecomunicaciones (caso de prueba)"
CONDICIONES = "caso de prueba de la hoja: rendimiento supuesto"
#: Quien guarda la version `001` de las plantillas (RF-83: toda version se confirma a nombre de
#: alguien; `scripts/generar_base_prueba.py` las corre fuera de pytest, sin el usuario de prueba).
USUARIO_DE_LA_PLANTILLA = "Plantilla <plantilla>"


def _lista(sesion, nombre: str, moneda: str, fecha: date) -> models.ListaPrecios:
    lista = models.ListaPrecios(
        nombre=nombre, moneda=moneda, fecha_vigencia=fecha, origen="caso de prueba"
    )
    sesion.add(lista)
    sesion.flush()
    return lista


def plantilla_of001(ruta: Path) -> Path:
    """OF-001: catalogo de sus 30 partidas, version `001` y su espacio guardado."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    crear_esquema_espacio(motor)
    try:
        with abrir_sesion(motor) as sesion:
            con_anexos_de_cadena(sesion)  # la cadena cubre el espacio que se guarda abajo
            lista = _lista(sesion, "Lista MaPreX jul-2026 (OF-001)", "USD", caso_of001.FECHA)
            catalogo = Catalogo(sesion)
            for composicion in caso_of001.COMPOSICIONES.values():
                catalogo.cargar_composicion(
                    composicion, lista, Dominio.CIVIL, caso_of001.FECHA, CONDICIONES
                )
            proyecto = crear_proyecto(sesion, NOMBRE_OF001, dominio=Dominio.CIVIL)
            espacio = espacio_of001()
            resultado = hoja.elaborar_hoja(
                espacio,
                caso_of001.COMPOSICIONES,
                codigo="001",
                fecha=caso_of001.FECHA,
                especialidad=hoja.TODAS,
                parametros=caso_ti001.PARAMETROS,
                moneda=caso_of001.MONEDA,
                plan=plan_secuencial,
            )
            version = guardar_presupuesto(
                sesion,
                resultado.elaboracion.presupuesto,
                resultado.elaboracion.informe,
                proyecto=proyecto,
                lista=lista,
                parametros=caso_ti001.PARAMETROS,
                pendientes=resultado.elaboracion.pendientes,
                plan=resultado.plan,
                usuario=USUARIO_DE_LA_PLANTILLA,
            )
            guardar_espacio(sesion, version.id, espacio)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


def plantilla_ti001(ruta: Path) -> Path:
    """TI-001: catalogo de sus partidas y version `001` con su plan; sin espacio (FR-5)."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    try:
        with abrir_sesion(motor) as sesion:
            lista = _lista(sesion, "Lista MaPreX jul-2026 (TI-001)", "USD", caso_ti001.FECHA)
            catalogo = Catalogo(sesion)
            for composicion in caso_ti001.COMPOSICIONES.values():
                catalogo.cargar_composicion(
                    composicion, lista, Dominio.TELECOM, caso_ti001.FECHA, CONDICIONES
                )
            proyecto = crear_proyecto(sesion, NOMBRE_TI001, dominio=Dominio.TELECOM)
            resultado = caso_ti001.elaborar_caso()
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=lista,
                parametros=caso_ti001.PARAMETROS,
                pendientes=resultado.pendientes,
                plan=caso_ti001.PLAN,
                usuario=USUARIO_DE_LA_PLANTILLA,
            )
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


def borrar_instantanea(sesion, proyecto: str, codigo: str = "001") -> None:
    """Deja la version como la dejaba el sistema anterior a SF-E6: sin instantanea ni plan."""
    from sqlalchemy import delete

    modelo = sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one()
    composiciones = select(models.ComposicionVersion.id).where(
        models.ComposicionVersion.presupuesto_id == modelo.id
    )
    sesion.execute(
        delete(models.LineaComposicionVersion).where(
            models.LineaComposicionVersion.composicion_id.in_(composiciones)
        )
    )
    sesion.execute(
        delete(models.ComposicionVersion).where(
            models.ComposicionVersion.presupuesto_id == modelo.id
        )
    )
    sesion.execute(delete(models.PlanVersion).where(models.PlanVersion.presupuesto_id == modelo.id))
    sesion.commit()
