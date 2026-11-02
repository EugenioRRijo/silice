"""Lo compartido por las pruebas del costo por tonelada del periodo (plan vial, Tarea 4). FICTICIOS.

Solo funciones simples (sin `@pytest.fixture`): cada modulo de prueba declara sus fixtures y las
llama. Nada de esto sale del codigo bajo prueba: los materiales, recetas, producciones y costos se
siembran con los servicios ya aprobados de `produccion/` (Tareas 1 y 3); la lista de precios con
`models.*` y las tasas con `registrar_importacion` (el camino de UC-17).

La planta de noviembre de 2026 (todo ficticio):

- `AGR-12` y `AGR-34`, agregados en t; `MZ-1`, mezcla con receta (`RECETA_A`, desde el
  2026-10-01): 0,94 t de `AGR-12` propio, 0,05 t de cemento asfaltico `CA-30` comprado y 8 l de
  gasoil `GO` comprado.
- Produccion: 150 t de `AGR-12` y 50 t de `AGR-34` el 05/11; 100 t de `MZ-1` el 10/11.
- Lista de la carpeta en USD desde el 01/11: `CA-30` a 600 USD/t y `GO` a 0,5 USD/l.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from produccion.costos import CostoDelPeriodo, registrar_costo
from produccion.inventario import crear_material, registrar_entrada
from produccion.modelo import METADATA_PRODUCCION, Material
from produccion.receta import Componente, producir_con_receta, registrar_receta
from tests.fixtures.hoja_versiones_api import registrar_tasa_en

D = Decimal
PERIODO = "2026-11"
AHORA = datetime(2026, 11, 30, 18, 0, 0)
USUARIO = "ana"
OCTUBRE = date(2026, 10, 1)

RECETA_A = (
    Componente("AGR-12", D("0.94"), "t", "propio"),
    Componente("CA-30", D("0.05"), "t", "comprado"),
    Componente("GO", D("8"), "l", "comprado"),
)
#: La receta que entra a mitad de mes (desde el 16/11): 0,95 + 0,04 = 0,99 t y 10 l de gasoil.
RECETA_B = (
    Componente("AGR-12", D("0.95"), "t", "propio"),
    Componente("CA-30", D("0.04"), "t", "comprado"),
    Componente("GO", D("10"), "l", "comprado"),
)
LISTA_USD = {"CA-30": ("600", "t"), "GO": ("0.5", "l")}
#: Los mismos precios en Bs con la tasa ficticia de 36,50 Bs/USD: 600 x 36,50 = 21.900 y
#: 0,5 x 36,50 = 18,25.
LISTA_BS = {"CA-30": ("21900", "t"), "GO": ("18.25", "l")}
TASA = "36.50"


def dia(n: int) -> date:
    return date(2026, 11, n)


def materiales(ins: Session, *, mezcla_en: str = "t", densidad: str | None = None) -> None:
    for codigo in ("AGR-12", "AGR-34"):
        crear_material(ins, codigo=codigo, nombre=codigo, unidad_venta="t", existencia_minima=D(0))
    crear_material(
        ins,
        codigo="MZ-1",
        nombre="Mezcla asfaltica ficticia",
        unidad_venta=mezcla_en,
        existencia_minima=D(0),
        densidad_t_m3=None if densidad is None else D(densidad),
    )


def receta(ins: Session, componentes=RECETA_A, desde: date = OCTUBRE) -> int:
    return registrar_receta(
        ins,
        "MZ-1",
        componentes,
        fuente="dosificacion ficticia",
        vigente_desde=desde,
        usuario=USUARIO,
        ahora=AHORA,
    )


def entrada(ins: Session, codigo: str, toneladas: str, fecha: date) -> None:
    material = ins.scalar(select(Material).where(Material.codigo == codigo))
    registrar_entrada(ins, material.id, fecha, D(toneladas), usuario=USUARIO, ahora=AHORA)


def producir(ins: Session, toneladas: str, fecha: date) -> None:
    producir_con_receta(ins, "MZ-1", D(toneladas), fecha, usuario=USUARIO, ahora=AHORA)


def planta(ins: Session, **material) -> None:
    """Materiales, `RECETA_A` y la produccion de noviembre (150 + 50 t de agregados, 100 t de
    mezcla)."""
    materiales(ins, **material)
    receta(ins)
    entrada(ins, "AGR-12", "150", dia(5))
    entrada(ins, "AGR-34", "50", dia(5))
    producir(ins, "100", dia(10))


def costo(ins: Session, centro: str, monto: str, moneda: str, fecha: date, concepto="otro") -> int:
    registro = CostoDelPeriodo(
        PERIODO, centro, concepto, D(monto), moneda, fecha, fuente="factura ficticia"
    )
    return registrar_costo(ins, registro, usuario=USUARIO, ahora=AHORA)


def costos_usd(ins: Session) -> None:
    """Cantera 600 + 400 = 1.000 USD; planta 1.200 USD."""
    costo(ins, "cantera", "600", "USD", dia(3), "gasoil")
    costo(ins, "cantera", "400", "USD", dia(4), "nomina")
    costo(ins, "planta", "1200", "USD", dia(12), "energia")


def lista(
    caso: Session,
    moneda: str,
    vigencia: date,
    precios: dict[str, tuple[str, str]],
    nombre: str = "Lista ficticia",
) -> int:
    """Una lista global de la carpeta; da de alta los insumos que falten (material)."""
    nueva = models.ListaPrecios(nombre=nombre, moneda=moneda, fecha_vigencia=vigencia)
    caso.add(nueva)
    caso.flush()
    for codigo, (precio, unidad) in precios.items():
        insumo = caso.scalar(select(models.Insumo).where(models.Insumo.codigo == codigo))
        if insumo is None:
            insumo = models.Insumo(
                codigo=codigo, tipo="material", descripcion=f"{codigo} ficticio", unidad=unidad
            )
            caso.add(insumo)
            caso.flush()
        caso.add(models.PrecioInsumo(lista_id=nueva.id, insumo_id=insumo.id, precio=D(precio)))
    caso.flush()
    return nueva.id


def tasas(caso: Session, dias: dict[date, str]) -> None:
    """Una importacion de la tasa BCV por dia (huellas distintas)."""
    for n, (fecha, valor) in enumerate(sorted(dias.items())):
        registrar_tasa_en(caso, fecha, valor, huella=f"{n:x}" * 64)


@contextmanager
def instalacion_en_memoria() -> Iterator[Session]:
    """Una instalacion vacia (solo las tablas de produccion) en memoria."""
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    try:
        with Session(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


@contextmanager
def carpeta_del_caso(directorio: Path) -> Iterator[Session]:
    """Una carpeta de caso nueva y migrada; lo que quede sin confirmar se deshace."""
    ruta = directorio / "carpeta.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield sesion
            sesion.rollback()
    finally:
        motor.dispose()


def noviembre_usd(ins: Session, caso: Session) -> None:
    """La planta, los costos en USD y la lista en USD de la carpeta: el calculo da
    `AGR-12` 5, `AGR-34` 5 y `MZ-1` 50,70."""
    planta(ins)
    costos_usd(ins)
    lista(caso, "USD", dia(1), LISTA_USD)
