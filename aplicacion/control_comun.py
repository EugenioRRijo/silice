"""Lo común del control de obra (UC-19 y UC-20): los textos y las columnas de la pantalla,
`ControlInvalido` y las ayudas que leen fechas y decimales, presentan montos e índices y
confirman o deshacen cada escritura. No importa nada de `aplicacion`: los cuatro módulos del
control lo toman de aquí sin cerrar un ciclo con la fachada.

Salió de `aplicacion/control.py` sin cambios (tarea 4.3 del plan de desenredo);
`aplicacion.control` lo reexporta.
"""

from __future__ import annotations

from collections.abc import Sequence
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
    """La fecha AAAA-MM-DD del campo `que` (su nombre en la pantalla). Vacía o ilegible, un
    `ControlInvalido` que nombra el campo como lo ve la persona (prueba en vivo 2026-11-18)."""
    if not texto.strip():
        raise ControlInvalido(f"Falta la fecha «{que}».")
    try:
        return date.fromisoformat(texto.strip()[:10])
    except ValueError:
        raise ControlInvalido(f"«{que}»: «{texto.strip()}» no es una fecha válida.") from None


def _decimal(texto: str, que: str) -> Decimal:
    """El número del campo `que` (su nombre en la pantalla; la pantalla ya lo manda con punto).
    Vacío o ilegible, un `ControlInvalido` que nombra el campo sin repetir lo enviado."""
    if not str(texto).strip():
        raise ControlInvalido(f"Falta la cifra «{que}».")
    try:
        valor = Decimal(str(texto).strip())
    except InvalidOperation:
        raise ControlInvalido(f"«{que}» no es un número válido.") from None
    if not valor.is_finite():
        raise ControlInvalido(f"«{que}» no es un número finito.")
    return valor


def _exigir_texto(texto: str, mensaje: str) -> None:
    """`ControlInvalido(mensaje)` si `texto` está en blanco: el núcleo diría «la fuente del cambio
    es obligatoria» aunque el campo de la pantalla se llame «Motivo»."""
    if not texto.strip():
        raise ControlInvalido(mensaje)


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


_PREFIJO_VALUACION = "valuacion:"


def _valuacion_del_hallazgo(origen_ids: Sequence[str], claves: Sequence[str]) -> str | None:
    """La clave de la valuación que cita un hallazgo de R13-R14, o `None` si no cita ninguna.

    El núcleo cita `valuacion:<clave>` o `valuacion:<clave>:<código>`; un R13 de una partida no
    programada cita solo el origen de la partida, sin ese prefijo. La clave se coteja contra las
    valuaciones registradas (`claves`) porque puede llevar «:» por dentro («VAL:01»): casa entera o
    seguida de «:», y entre dos que casan gana la más larga."""
    for origen in origen_ids:
        if not origen.startswith(_PREFIJO_VALUACION):
            continue
        resto = origen.removeprefix(_PREFIJO_VALUACION)
        casan = [c for c in claves if resto == c or resto.startswith(f"{c}:")]
        if casan:
            return max(casan, key=len)
    return None
