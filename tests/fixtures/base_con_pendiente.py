"""Un presupuesto base guardado con items pendientes (UC-01 3a), para las pruebas de recarga y de
escenarios (INV-080, INV-083).

La recarga (`tests/integration/test_recarga_con_pendientes.py`), la pagina de escenarios
(`tests/unit/test_ui_escenarios.py`) y la ruta de la API
(`tests/integration/test_api_escenarios.py`) parten de la misma base (INV-052: lo compartido
entre pruebas vive en `tests/fixtures/`), guardada por el nucleo directo con `pendientes=`, sin
pasar por la capa que se prueba. La ruta del archivo la elige la prueba y vive en `tmp_path`:
nada escribe en `data/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from core import models
from core.budget import ResultadoElaboracion, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts import Dominio, ItemComputo, OrigenTipo
from scripts.seed import sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import items_auditados

#: El item cuya partida no existe en el catalogo sembrado (UC-01, flujo 3a).
PENDIENTE_T99 = ItemComputo(
    codigo_partida="XX-99-NUE",
    descripcion="Excavacion de un foso nuevo",
    unidad="m3",
    cantidad=Decimal("2.5"),
    origen_id="T-99",
    origen_tipo=OrigenTipo.MANUAL,
    dominio=Dominio.CIVIL,
)


def url_sqlite(ruta: Path) -> str:
    """La URL de SQLAlchemy de un archivo SQLite."""
    return f"sqlite:///{ruta.as_posix()}"


def elaborar_en(
    sesion: Session, items: Sequence[ItemComputo], codigo: str = linea_base.CODIGO_PRESUPUESTO
) -> ResultadoElaboracion:
    """La elaboracion de la interfaz y de la API: composiciones solo de las partidas que existen,
    con los parametros y la fecha de la linea base."""
    catalogo = Catalogo(sesion)
    existentes = {partida.codigo for partida in catalogo.partidas()}
    composiciones = catalogo.composiciones(
        dict.fromkeys(i.codigo_partida for i in items if i.codigo_partida in existentes),
        fecha=linea_base.FECHA_LINEA_BASE,
    )
    return elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
    )


def guardar_en(
    sesion: Session, proyecto: models.Proyecto, resultado: ResultadoElaboracion, **extra
) -> models.Presupuesto:
    """`guardar_presupuesto` con la lista vigente y los parametros de la linea base; `extra` pasa
    tal cual (p. ej. `pendientes=`). No confirma."""
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=Catalogo(sesion).lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
        **extra,
    )


def emitir(ruta: Path, items: Sequence[ItemComputo]) -> ResultadoElaboracion:
    """Siembra `ruta`, elabora `items`, guarda con sus pendientes y confirma; cierra el motor.

    Quien abra `ruta` despues lee lo persistido, no la identidad de una sesion viva.
    """
    motor = crear_motor(url_sqlite(ruta))
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            resultado = elaborar_en(sesion, items)
            guardar_en(sesion, proyecto, resultado, pendientes=resultado.pendientes)
            sesion.commit()
    finally:
        motor.dispose()
    return resultado


def guardar_base_con_pendiente(ruta: Path) -> ResultadoElaboracion:
    """El presupuesto 001 (linea base mas T-99) guardado en `ruta` con su pendiente."""
    resultado = emitir(ruta, [*items_auditados(), PENDIENTE_T99])
    assert resultado.pendientes == (PENDIENTE_T99,)
    return resultado
