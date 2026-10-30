"""Costos del periodo de la cantera y la planta (Tarea 1 del plan vial).

Dominio puro: solo biblioteca estandar, SQLAlchemy y `produccion.modelo`. Cada costo trae su
periodo (`AAAA-MM`), centro, concepto, monto en `Decimal`, moneda original, fecha y fuente. Nada se
sobrescribe: anular un costo inserta una fila nueva (`anula_id`) y deja el original intacto. El
servicio hace `flush`; quien llama decide el `commit`.

`anulado` de un `CostoRegistrado` es verdadero tanto en el costo anulado como en la fila de
anulacion que lo anula: ninguno de los dos cuenta para los costos del periodo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from produccion.modelo import Costo

CONCEPTOS = ("gasoil", "equipo", "nomina", "mantenimiento", "explosivos", "energia", "otro")
CENTROS = ("cantera", "planta")
MONEDAS = ("Bs", "USD")
_PERIODO = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


class ErrorDeCosto(ValueError):  # noqa: N818 - empieza por Error, como ErrorDeInventario
    """Dato de costo invalido; el mensaje esta escrito para el usuario."""


class CostoInexistente(ErrorDeCosto):
    """No hay un costo con ese numero: la API lo responde 404."""


class CostoYaAnulado(ErrorDeCosto):
    """El costo ya fue anulado (o es una anulacion): la API lo responde 409."""


def validar_periodo(periodo: str) -> tuple[int, int]:
    """`(anio, mes)` de un periodo `AAAA-MM`; `ErrorDeCosto` si no lo es."""
    coincide = _PERIODO.match(periodo) if isinstance(periodo, str) else None
    if coincide is None:
        raise ErrorDeCosto(
            f"El periodo debe ser AAAA-MM, con mes de 01 a 12: «{str(periodo)[:20]}»."
        )
    return int(coincide.group(1)), int(coincide.group(2))


@dataclass(frozen=True)
class CostoDelPeriodo:
    periodo: str
    centro: str
    concepto: str
    monto: Decimal
    moneda: str
    fecha: date
    fuente: str
    nota: str = ""

    def __post_init__(self) -> None:
        anio, mes = validar_periodo(self.periodo)
        if self.centro not in CENTROS:
            raise ErrorDeCosto(f"El centro (centro) debe ser uno de: {', '.join(CENTROS)}.")
        if self.concepto not in CONCEPTOS:
            raise ErrorDeCosto(f"El concepto (concepto) debe ser uno de: {', '.join(CONCEPTOS)}.")
        if self.moneda not in MONEDAS:
            raise ErrorDeCosto("La moneda (moneda) debe ser Bs o USD.")
        if (
            not isinstance(self.monto, Decimal)
            or not self.monto.is_finite()
            or self.monto < Decimal(0)
        ):
            raise ErrorDeCosto("El monto (monto) debe ser un número decimal de cero o más.")
        if self.monto.is_zero():  # -0 pasa a 0; el resto no se toca (no se redondea a 28 cifras)
            object.__setattr__(self, "monto", self.monto.copy_abs())
        if not isinstance(self.fecha, date) or isinstance(self.fecha, datetime):
            raise ErrorDeCosto("La fecha (fecha) del costo debe ser una fecha.")
        if (self.fecha.year, self.fecha.month) != (anio, mes):
            raise ErrorDeCosto(
                f"La fecha {self.fecha.isoformat()} queda fuera del periodo {self.periodo}."
            )
        if not self.fuente.strip():
            raise ErrorDeCosto("Indique la fuente del costo (por ejemplo, el número de factura).")


@dataclass(frozen=True)
class CostoRegistrado:
    id: int
    costo: CostoDelPeriodo
    usuario: str
    registrado: datetime
    anulado: bool
    anula_id: int | None = None
    motivo: str = ""


def _insertar(
    sesion: Session,
    costo: CostoDelPeriodo,
    *,
    usuario: str,
    ahora: datetime,
    anula_id: int | None = None,
    motivo: str = "",
) -> int:
    if not usuario.strip():
        raise ErrorDeCosto("Falta el usuario que registra el costo.")
    fila = Costo(
        periodo=costo.periodo,
        centro=costo.centro,
        concepto=costo.concepto,
        monto=costo.monto,
        moneda=costo.moneda,
        fecha=costo.fecha,
        fuente=costo.fuente.strip(),
        nota=costo.nota.strip(),
        usuario=usuario,
        registrado=ahora,
        anula_id=anula_id,
        motivo=motivo,
    )
    sesion.add(fila)
    sesion.flush()
    return fila.id


def registrar_costo(
    sesion: Session, costo: CostoDelPeriodo, *, usuario: str, ahora: datetime
) -> int:
    """Inserta el costo y devuelve su numero."""
    return _insertar(sesion, costo, usuario=usuario, ahora=ahora)


def _fue_anulado(sesion: Session, costo_id: int) -> bool:
    return sesion.scalar(select(Costo.id).where(Costo.anula_id == costo_id).limit(1)) is not None


def anular_costo(
    sesion: Session, costo_id: int, *, motivo: str, usuario: str, ahora: datetime
) -> int:
    """Anula un costo con una fila nueva (copia del original, con `anula_id` y el motivo). El
    original no cambia. Devuelve el numero de la fila de anulacion."""
    motivo = motivo.strip()
    if not motivo:
        raise ErrorDeCosto("Indique el motivo de la anulación.")
    original = sesion.get(Costo, costo_id)
    if original is None:
        raise CostoInexistente("No existe ese costo. Actualice la lista.")
    if original.anula_id is not None or _fue_anulado(sesion, costo_id):
        raise CostoYaAnulado("Ese costo ya fue anulado.")
    copia = CostoDelPeriodo(
        original.periodo,
        original.centro,
        original.concepto,
        original.monto,
        original.moneda,
        original.fecha,
        original.fuente,
        original.nota,
    )
    return _insertar(sesion, copia, usuario=usuario, ahora=ahora, anula_id=costo_id, motivo=motivo)


def costos_del_periodo(
    sesion: Session, periodo: str, *, incluir_anulados: bool = False
) -> list[CostoRegistrado]:
    """Los costos del periodo en orden de registro. Por omision solo los vigentes; con
    `incluir_anulados`, tambien los anulados y sus filas de anulacion (todos con `anulado`)."""
    validar_periodo(periodo)
    filas = list(sesion.scalars(select(Costo).where(Costo.periodo == periodo).order_by(Costo.id)))
    anulados = {f.anula_id for f in filas if f.anula_id is not None}
    salida: list[CostoRegistrado] = []
    for f in filas:
        anulado = f.anula_id is not None or f.id in anulados
        if anulado and not incluir_anulados:
            continue
        salida.append(
            CostoRegistrado(
                id=f.id,
                costo=CostoDelPeriodo(
                    f.periodo, f.centro, f.concepto, f.monto, f.moneda, f.fecha, f.fuente, f.nota
                ),
                usuario=f.usuario,
                registrado=f.registrado,
                anulado=anulado,
                anula_id=f.anula_id,
                motivo=f.motivo,
            )
        )
    return salida


def totales_por_centro(sesion: Session, periodo: str) -> list[tuple[str, str, Decimal]]:
    """Total vigente del periodo por (centro, moneda), sin convertir moneda. Un costo anulado y su
    fila de anulacion no suman. Orden estable: centro y luego moneda."""
    sumas: dict[tuple[str, str], Decimal] = {}
    for fila in costos_del_periodo(sesion, periodo):
        clave = (fila.costo.centro, fila.costo.moneda)
        sumas[clave] = sumas.get(clave, Decimal(0)) + fila.costo.monto
    return [(centro, moneda, total) for (centro, moneda), total in sorted(sumas.items())]
