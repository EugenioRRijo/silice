"""Lo común del control de obra (UC-19 y UC-20): los textos y las columnas de la pantalla,
`ControlInvalido` y las ayudas que leen fechas y decimales, presentan montos e índices y
confirman o deshacen cada escritura. No importa nada de `aplicacion`: los cuatro módulos del
control lo toman de aquí sin cerrar un ciclo con la fachada.

Salió de `aplicacion/control.py` sin cambios (tarea 4.3 del plan de desenredo);
`aplicacion.control` lo reexporta.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation

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


def _escribir(sesion: Session, accion, antes_de_confirmar: Callable[[], object] | None = None):
    """Corre `accion`, confirma si sale bien y deshace si no; un error de los datos sale como
    `ControlInvalido` (422) y cualquier otro se relanza tras deshacer. Un fallo de la base
    (`SQLAlchemyError`) no es culpa de lo enviado ni puede mostrar el texto del motor (regla C1):
    sigue al manejador común de la API, que lo registra y responde el 503 fijo (DS-113).

    `antes_de_confirmar()`, si se da, corre con lo de `accion` ya escrito (`flush`) y antes del
    `commit`, en la misma transacción, y lo que devuelve es lo que devuelve esta (patrón de DS-70:
    la API arma ahí su respuesta; tras el `commit`, consultar abriría otro `BEGIN IMMEDIATE`,
    DS-57). Si lanza, no queda nada escrito."""
    try:
        resultado = accion()
        if antes_de_confirmar is not None:
            sesion.flush()
            resultado = antes_de_confirmar()
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
    except BaseException:
        sesion.rollback()
        raise


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


#: Más largo que esto no es una frase del núcleo (la más larga mide ~200 caracteres): el catálogo
#: de regex lo devuelve intacto sin tocarlas, para que un texto hostil no cueste tiempo. El
#: desglose «no aplica (...)» no usa esas regex y no lleva tope.
LARGO_MAXIMO_A_CORREGIR = 2_000

#: Un hueco acotado: su expresión y, si lo que calza se presenta de otra forma (una fecha del
#: sistema en dd/mm/aaaa), la función que lo presenta.
Hueco = str | tuple[str, Callable[[str], str]]

#: Huecos con forma conocida: las cifras que el núcleo imprime. Acotarlos por clase hace lineal la
#: coincidencia (un `.+` voraz encadenado sería cúbico). Todo hueco no listado es texto del usuario
#: y cada plantilla tiene a lo sumo uno, de modo que tampoco encadena.
_HUECOS_NUMERICOS: dict[str, Hueco] = {
    "termino": r"\d+",
    "retraso": r"\d+",
    "plan": r"\d+",
    "spi": r"[-+0-9.,E]+",
    "cpi": r"[-+0-9.,E]+",
    "precio": r"[-+0-9.,E]+",
    "ev": r"[-+0-9.,E]+",
    "puntos": r"[-+0-9.,E]+",
}


def _expresion(hueco: Hueco) -> str:
    return hueco if isinstance(hueco, str) else hueco[0]


def _compilar(crudo: str, huecos: Mapping[str, Hueco] = _HUECOS_NUMERICOS) -> re.Pattern[str]:
    """La frase del núcleo como expresión: el texto fijo literal, cada hueco `{x}` un dato."""
    partes = re.split(r"\{(\w+)\}", crudo)
    libres = [h for h in partes[1::2] if h not in huecos]
    if len(libres) > 1:
        raise ValueError(f"la plantilla {crudo!r} encadena huecos de texto libre")
    patron = "".join(
        f"(?P<{p}>{_expresion(huecos[p]) if p in huecos else '.+'})" if i % 2 else re.escape(p)
        for i, p in enumerate(partes)
    )
    return re.compile(patron, re.DOTALL)


def catalogo_de_frases(
    plantillas: Sequence[tuple[str, str]],
    huecos: Mapping[str, Hueco] = _HUECOS_NUMERICOS,
    *,
    largo_maximo: int = LARGO_MAXIMO_A_CORREGIR,
) -> Callable[[str], str]:
    """El corrector de un catálogo de frases fijas del núcleo (T8b; lo usa también Reajuste).

    Devuelve una función pura que, si el texto COMPLETO calza con una plantilla, lo reescribe con su
    versión con tildes; si no, lo devuelve igual. Lo que calza en un hueco libre (texto del usuario)
    vuelve tal cual; un hueco acotado con función (una fecha) se presenta con ella. Más largo que
    `largo_maximo` vuelve intacto sin probar ninguna expresión. Cada plantilla lleva a lo sumo un
    hueco libre (`_compilar` lo exige), así que el costo es lineal en el largo.
    """
    compilado = tuple((_compilar(crudo, huecos), con_tilde) for crudo, con_tilde in plantillas)
    presentar = {nombre: h[1] for nombre, h in huecos.items() if not isinstance(h, str)}

    def corregir(texto: str) -> str:
        if len(texto) > largo_maximo:
            return texto
        for patron, con_tilde in compilado:
            calce = patron.fullmatch(texto)
            if calce is not None:
                return con_tilde.format(
                    **{
                        nombre: presentar[nombre](valor) if nombre in presentar else valor
                        for nombre, valor in calce.groupdict().items()
                    }
                )
        return texto

    return corregir
