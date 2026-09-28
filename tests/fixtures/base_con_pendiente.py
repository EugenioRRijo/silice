"""Un presupuesto base guardado con un item pendiente (UC-01 3a), para las pruebas de INV-083.

La pagina de escenarios (`tests/unit/test_ui_escenarios.py`) y la ruta de la API
(`tests/integration/test_api_escenarios.py`) prueban lo mismo por dos capas: los escenarios de un
base con pendientes los declaran. Las dos parten de esta misma base (INV-052: lo compartido entre
pruebas vive en `tests/fixtures/`), guardada por el nucleo directo con `pendientes=`, sin pasar por
la capa que se prueba. La ruta la elige la prueba y vive en `tmp_path`: nada escribe en `data/`.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from core.budget import elaborar, guardar_presupuesto, plan_secuencial
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


def guardar_base_con_pendiente(ruta: Path) -> None:
    """Siembra `ruta` y guarda el presupuesto 001 (linea base mas T-99) con su pendiente.

    Cierra el motor al terminar: quien lo abra despues lee lo persistido, no la identidad de una
    sesion viva.
    """
    motor = crear_motor(url_sqlite(ruta))
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            resultado = elaborar(
                [*items_auditados(), PENDIENTE_T99],
                catalogo.composiciones(
                    linea_base.CODIGOS_LINEA_BASE, fecha=linea_base.FECHA_LINEA_BASE
                ),
                linea_base.PARAMETROS_LINEA_BASE,
                codigo=linea_base.CODIGO_PRESUPUESTO,
                fecha=linea_base.FECHA_LINEA_BASE,
                moneda=linea_base.MONEDA,
                plan=plan_secuencial,
            )
            assert resultado.pendientes == (PENDIENTE_T99,)
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                parametros=linea_base.PARAMETROS_LINEA_BASE,
                pendientes=resultado.pendientes,
            )
            sesion.commit()
    finally:
        motor.dispose()
