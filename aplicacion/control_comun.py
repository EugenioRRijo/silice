"""Lo común del control de obra (UC-19 y UC-20): los textos y las columnas de la pantalla,
`ControlInvalido` y las ayudas que leen fechas y decimales, presentan montos e índices y
confirman o deshacen cada escritura. No importa nada de `aplicacion`: los cuatro módulos del
control lo toman de aquí sin cerrar un ciclo con la fachada.

Salió de `aplicacion/control.py` sin cambios (tarea 4.3 del plan de desenredo);
`aplicacion.control` lo reexporta.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.budget.valuaciones import LineaBaseInvalidada
from core.verification.texto import formatear_decimal

METODO_NINGUNO = "Sin precios del corte"
METODO_COMPROBACION = "Comprobacion directa (version revalorada)"
METODO_ESCALATORIA = "Escalatoria (un Km declarado)"
METODO_DECLARADOS = "Precios declarados de insumos"
METODOS_DE_PRECIOS = (
    METODO_NINGUNO,
    METODO_COMPROBACION,
    METODO_ESCALATORIA,
    METODO_DECLARADOS,
)
#: Elegir los precios declarados sin ninguno hasta el corte (MP-7, Tarea 25).
MENSAJE_SIN_DECLARADOS = (
    "No hay precios declarados de insumos hasta el corte: declárelos desde Estudio de mercado o "
    "al recibir una compra en Procura."
)
COLUMNAS_LINEAS = ("Partida", "Cantidad", "Fecha de medicion", "Observacion")
COLUMNAS_VALUACIONES = (
    "Numero",
    "Periodo",
    "Fecha",
    "Inspector",
    "Registrada",
    "Estado",
    "Subtotal",
    "IVA",
    "Total con IVA",
)
COLUMNAS_INDICADORES = ("Indicador", "Valor", "En la otra moneda", "Nota")
COLUMNAS_ALERTAS = ("Alerta", "Severidad", "Descripcion", "Observado", "Umbral")
COLUMNAS_REPROYECCION = ("Partida", "Indice", "Fin (dia habil)", "Nota")
COLUMNAS_OPCIONES = (
    "Opcion",
    "Termino",
    "Retraso (dias)",
    "Costo directo adicional",
    "Costo indirecto",
    "Penalizacion",
    "Punto de equilibrio",
    "Nota",
)
COLUMNAS_DECISIONES = ("Version", "Opcion", "Corte", "Termino", "Fuente", "Responsable")
NO_DISPONIBLE = "no disponible"
NO_APLICA = "no aplica"
NATURALEZA_SUPUESTO = "SUPUESTO_DECLARADO"
NATURALEZA_DATO = "DATO_DEL_CONTRATO"


class ControlInvalido(ValueError):  # noqa: N818
    """Algo del control no se pudo hacer; el mensaje dice qué pasó y cómo arreglarlo."""


def _monto(valor: Decimal | None) -> str:
    return NO_DISPONIBLE if valor is None else formatear_decimal(valor, 2)


def _indice(valor: Decimal | None) -> str:
    return NO_APLICA if valor is None else formatear_decimal(valor, 4)


def _fecha(texto: str, que: str) -> date:
    try:
        return date.fromisoformat(texto.strip()[:10])
    except ValueError:
        raise ControlInvalido(f"{que}: {texto!r} no es una fecha (AAAA-MM-DD)") from None


def _decimal(texto: str, que: str) -> Decimal:
    try:
        valor = Decimal(str(texto).strip())
    except InvalidOperation:
        raise ControlInvalido(f"{que}: {texto!r} no es un numero decimal") from None
    if not valor.is_finite():
        raise ControlInvalido(f"{que}: {texto!r} no es un numero finito")
    return valor


def _escribir(sesion: Session, accion):
    """Corre `accion`, confirma si sale bien y deshace si no; todo error sale como
    `ControlInvalido`."""
    try:
        resultado = accion()
        sesion.commit()
        return resultado
    except ControlInvalido:
        sesion.rollback()
        raise
    except LineaBaseInvalidada as error:
        sesion.rollback()
        raise ControlInvalido(str(error)) from error
    except (ValueError, KeyError) as error:
        sesion.rollback()
        raise ControlInvalido(
            str(error.args[0] if isinstance(error, KeyError) else error)
        ) from error
    except SQLAlchemyError as error:
        sesion.rollback()
        raise ControlInvalido(
            f"No se pudo escribir en el caso: {getattr(error, 'orig', error)}"
        ) from error
