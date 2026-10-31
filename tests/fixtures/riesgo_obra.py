"""Una vía ficticia para «Riesgo de la obra» (plan vial, Tarea 16). Datos FICTICIOS, ninguno real.

La obra «Vía Ficticia Riesgo» tiene dos versiones en USD, VR-001 (con línea base de control que
empieza el 01/02/2027) y VR-002 (sin línea base), con las mismas tres partidas de un solo material
y los parámetros de costo en cero, así el total es la suma de cantidad × precio, a mano:

- VIA-01: 1 × (1 t de «Cemento asfáltico» a 600) = 600
- VIA-02: 2 × (100 l de «Gasoil» a 0,50) = 100
- VIA-03: 1 × (1 u de «Señalización» a 300) = 300

Total base: 1.000 USD.

Series (25 meses, de enero de 2025 a enero de 2027): el PPI de asfalto sube 10 % cada mes con
valores enteros exactos (`11^i × 10^(24 − i)`), así cada variación es exactamente 1,1 y todas las
trayectorias dan lo mismo; el gasoil queda en 0,50 USD/l y la tasa BCV en 40,00 Bs/USD (una
observación el día 15 de cada mes). Con el gasoil quieto, solo el asfalto se mueve.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from aplicacion.riesgo.series import CEMENTO_ASFALTICO_PPI, GASOIL_USD
from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto, plan_secuencial
from core.budget.valuaciones import Calendario, registrar_linea_base
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.catalog.indices import (
    LADO_POR_DEFECTO,
    DefinicionSerie,
    Observacion,
    definicion_tasa,
    registrar_importacion,
)
from core.contracts.apu import ComposicionAPU, LineaMaterial, ParametrosCosto
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from operacion.base_datos import preparar_base

D = Decimal
OBRA = "Vía Ficticia Riesgo"
CON_LINEA_BASE = "VR-001"
SIN_LINEA_BASE = "VR-002"
ARCHIVO = "via_riesgo.db"
FECHA = date(2026, 12, 15)
INICIO_DE_LA_LINEA_BASE = date(2027, 2, 1)
PARAMETROS = ParametrosCosto(fcas=D(0), bono_alimentacion=D(0), administracion=D(0), utilidad=D(0))
ASFALTO = "Cemento asfáltico"
GASOIL = "Gasoil"
SENALES = "Señalización"
MAPA = {ASFALTO: CEMENTO_ASFALTICO_PPI.codigo, GASOIL: GASOIL_USD.codigo}
#: Enero de 2025 a enero de 2027.
MESES = [date(2025 + (m // 12), m % 12 + 1, 1) for m in range(25)]

#: (código, insumo, unidad, cantidad del material por unidad de partida, precio, cantidad)
PARTIDAS = (
    ("VIA-01", ASFALTO, "t", "1", "600", "1"),
    ("VIA-02", GASOIL, "l", "100", "0.5", "2"),
    ("VIA-03", SENALES, "u", "1", "300", "1"),
)


def _composicion(codigo: str, insumo: str, unidad: str, por_unidad: str, precio: str):
    return ComposicionAPU(
        codigo_partida=codigo,
        descripcion=f"Partida ficticia {codigo}",
        unidad="u",
        rendimiento=D(1),
        materiales=(LineaMaterial(insumo, unidad, D(por_unidad), D(precio)),),
    )


COMPOSICIONES = {fila[0]: _composicion(*fila[:5]) for fila in PARTIDAS}


def _items() -> list[ItemComputo]:
    return [
        ItemComputo(
            codigo_partida=codigo,
            descripcion=f"Partida ficticia {codigo}",
            unidad="u",
            cantidad=D(cantidad),
            origen_id=f"FILA-{n}",
            origen_tipo=OrigenTipo.TABULAR,
            dominio=Dominio.CIVIL,
        )
        for n, (codigo, *_resto, cantidad) in enumerate(PARTIDAS, 1)
    ]


def _version(sesion: Session, proyecto, lista, codigo: str) -> None:
    resultado = elaborar(
        _items(),
        COMPOSICIONES,
        PARAMETROS,
        codigo=codigo,
        fecha=FECHA,
        moneda="USD",
        plan=plan_secuencial,
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=lista,
        parametros=PARAMETROS,
        pendientes=resultado.pendientes,
        usuario="Ana <ana>",
    )
    sesion.flush()


def _serie(sesion: Session, definicion: DefinicionSerie, valores: dict[date, Decimal]) -> None:
    registrar_importacion(
        sesion,
        definicion,
        [Observacion(f, v) for f, v in sorted(valores.items())],
        archivo="ficticio.csv",
        huella=definicion.codigo.encode().hex()[:64].ljust(64, "0"),
        fuente="serie ficticia de prueba",
        fecha_descarga=date(2027, 2, 1),
        responsable="Prueba",
        filas_leidas=len(valores),
        filas_rechazadas=0,
        ahora=datetime(2027, 2, 1, 8, 0),
    )


def sembrar_series(sesion: Session) -> None:
    """PPI que sube 10 % exacto cada mes, gasoil en 0,50 y tasa en 40,00 (véase el encabezado)."""
    n = len(MESES) - 1
    ppi = {m: D(11**i * 10 ** (n - i)) for i, m in enumerate(MESES)}
    _serie(sesion, CEMENTO_ASFALTICO_PPI, ppi)
    _serie(sesion, GASOIL_USD, dict.fromkeys(MESES, D("0.50")))
    _serie(
        sesion,
        definicion_tasa(LADO_POR_DEFECTO),
        {m.replace(day=15): D("40.00") for m in MESES},
    )


def crear_via(ruta: Path) -> Path:
    """La carpeta del caso con la obra, sus dos versiones, la línea base de VR-001 y las series."""
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            lista = models.ListaPrecios(
                nombre="Lista USD ficticia", moneda="USD", fecha_vigencia=FECHA, origen="prueba"
            )
            sesion.add(lista)
            sesion.flush()
            catalogo = Catalogo(sesion)
            for composicion in COMPOSICIONES.values():
                catalogo.cargar_composicion(composicion, lista, Dominio.CIVIL, FECHA, "prueba")
            proyecto = crear_proyecto(sesion, OBRA, dominio=Dominio.CIVIL)
            _version(sesion, proyecto, lista, CON_LINEA_BASE)
            _version(sesion, proyecto, lista, SIN_LINEA_BASE)
            registrar_linea_base(
                sesion,
                OBRA,
                CON_LINEA_BASE,
                desde=FECHA,
                perspectiva="costo",
                calendario=Calendario(INICIO_DE_LA_LINEA_BASE, 22),
                fuente="línea base ficticia",
                responsable="Ana",
                ahora=datetime(2026, 12, 20, 9, 0),
            )
            sembrar_series(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta
