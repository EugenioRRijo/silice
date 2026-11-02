"""Una carpeta de trabajo ficticia en Bs con dos obras sin versiones (Tarea 12 del plan de montar un
presupuesto: Elaborar lleva sus ítems a la Hoja).

La lista «Lista Bs de prueba» (vigente desde el 01/10/2026) trae OBRA-01 a OBRA-06 de
`tests/fixtures/carpeta_aprobaciones.py` (una línea de material, una de equipo y una de mano de obra
cada una, números inventados); la carpeta declara Bs; la obra `VIVIENDA` está en Bs y `CASA_USD` en
USD. Con `con_tasa`, la tasa del BCV del 24/10/2026 a 40,00 Bs/USD (ficticia). Es la misma carpeta
que arma `tests/unit/test_api_hoja_partidas.py` (Tarea 9), escrita aparte para no depender de un
módulo de pruebas ajeno. Ningún precio ni nombre real.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core import models
from core.budget import crear_proyecto
from core.budget.moneda import declarar_moneda
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.dominio import Dominio
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import COMPOSICIONES
from tests.fixtures.hoja_versiones_api import registrar_tasa

FECHA_LISTA = date(2026, 10, 1)
FECHA_TASA = date(2026, 10, 24)
VIVIENDA = "Vivienda Demo 80 m2"
CASA_USD = "Casa Demo en USD"


def carpeta_en_bs(ruta: Path, *, con_tasa: bool) -> Path:
    """Prepara en `ruta` la carpeta ficticia en Bs con VIVIENDA (Bs) y CASA_USD (USD)."""
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            lista = models.ListaPrecios(
                nombre="Lista Bs de prueba",
                moneda="Bs",
                fecha_vigencia=FECHA_LISTA,
                origen="prueba",
            )
            sesion.add(lista)
            sesion.flush()
            catalogo = Catalogo(sesion)
            for composicion in COMPOSICIONES.values():
                catalogo.cargar_composicion(
                    composicion, lista, Dominio.CIVIL, FECHA_LISTA, "prueba"
                )
            declarar_moneda_de_la_carpeta(
                sesion, "Bs", responsable="Ana <ana>", ahora=datetime(2026, 10, 1, 8, 0)
            )
            for nombre, moneda in ((VIVIENDA, "Bs"), (CASA_USD, "USD")):
                proyecto = crear_proyecto(sesion, nombre, dominio=Dominio.CIVIL)
                declarar_moneda(sesion, proyecto, moneda, responsable="Ana <ana>")
            sesion.commit()
    finally:
        motor.dispose()
    if con_tasa:
        registrar_tasa(ruta, FECHA_TASA, "40.00")
    return ruta
