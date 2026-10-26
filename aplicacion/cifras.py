"""Las cifras que teclea la persona: coma para los decimales, punto para los miles.

Regla de producto de Eugenio (2026-10-25): «la coma para decimales y el punto para las decenas y
centenas (miles), para que no haya equivocaciones». Resuelve la decisión D-8 de la Hoja
(`docs/especificaciones/2026-10-19-hoja-react-design.md`) y el riesgo de Componer, que leía «1.000»
como uno (un precio mil veces menor).

Es el ÚNICO intérprete de lo que se escribe en un campo de cifra de la interfaz (Componer y la Hoja
lo llaman al recibir; `docs/bitacora/2026-10-25-coma-decimal-punto-miles.md` tiene el inventario).
Las pantallas cuyo contrato de API ya es un decimal con punto convierten en el navegador con
`frontend-desktop/src/indicadores/cifraEscrita.ts`, que cumple la misma tabla de oráculos
(`tests/fixtures/cifras_escritas.json`). Los archivos internos, los CSV de terceros, el `.silice` y
el contrato de la API siguen con el punto decimal: esto es solo para lo que la persona teclea.

Qué se acepta (después de quitar los blancos de los extremos):

- un signo menos opcional, pegado a la cifra («-0,5»); el «+» no;
- la parte entera sin separadores («1234») o agrupada de tres en tres con punto, sin cero a la
  izquierda del primer grupo («1.234», «12.345.678»);
- una parte decimal opcional tras UNA coma, con al menos una cifra («2,5», «0,005»).

Todo lo demás se rechaza con un mensaje llano, sin adivinar: «2.5» y «1.23» (decimal anglosajón),
«1,234.5», «1.2345», «0.123» (¿cero coma ciento veintitrés o ciento veintitrés?), «1,2,3», los
espacios entre las cifras (también «1 234»: el espacio de miles NO se acepta, para no confundirlo
con dos cifras pegadas), «,5», «5,», NaN, Infinity, exponentes («1e3»), «1_000» y las cifras que no
son 0-9 ASCII. Nunca pasa por coma flotante; el cero negativo se lee como cero.
"""

from __future__ import annotations

import re
from decimal import Decimal

__all__ = [
    "AYUDA_CIFRAS",
    "BLANCOS",
    "MENSAJE_CIFRA",
    "MENSAJE_CIFRA_VACIA",
    "CifraInvalida",
    "cifra_escrita",
    "texto_de_cifra",
]

#: Lo que se responde a una cifra mal escrita: la regla con sus dos ejemplos.
MENSAJE_CIFRA = (
    "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56."
)
#: Lo que se responde a un campo de cifra vacío (quien llama decide si vacío vale cero).
MENSAJE_CIFRA_VACIA = f"Escriba un número. {MENSAJE_CIFRA}"
#: Lo que se recorta en los bordes, y nada más: el mismo conjunto en el navegador
#: (`cifraEscrita.ts`). `str.strip()` y `String.trim()` recortan conjuntos distintos (el BOM, NEL).
BLANCOS = " \t\n\r\x0b\x0c\xa0\x85\ufeff"
#: El texto de ayuda junto a los campos de cifra.
AYUDA_CIFRAS = "Escriba los decimales con coma: 2,5; el punto separa los miles: 1.234,56."

# `[0-9]` y no `\d`: en Python `\d` también acepta cifras arábigas o de ancho completo.
_CIFRA = re.compile(r"(-?)([0-9]+|[1-9][0-9]{0,2}(?:\.[0-9]{3})+)(?:,([0-9]+))?")


class CifraInvalida(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """El texto no es una cifra escrita con la regla; el mensaje es el que ve la persona."""


def cifra_escrita(texto: str) -> Decimal:
    """El `Decimal` exacto de una cifra tecleada con coma decimal y punto de miles.

    `CifraInvalida` (un `ValueError`) con `MENSAJE_CIFRA_VACIA` si el campo está en blanco y con
    `MENSAJE_CIFRA` si no sigue la regla. El mensaje no repite lo escrito: quien llama añade el
    lugar (la tabla, la fila, el campo) y, si quiere, el texto.
    """
    limpio = texto.strip(BLANCOS)
    if not limpio:
        raise CifraInvalida(MENSAJE_CIFRA_VACIA)
    partes = _CIFRA.fullmatch(limpio)
    if partes is None:
        raise CifraInvalida(MENSAJE_CIFRA)
    signo, entera, decimales = partes.groups()
    valor = Decimal(f"{signo}{entera.replace('.', '')}" + (f".{decimales}" if decimales else ""))
    return valor.copy_abs() if valor.is_zero() else valor


def texto_de_cifra(valor: Decimal) -> str:
    """El `Decimal` como lo escribiría la persona en un campo: «1.234,5», «0,12», «3,000».

    Es lo que la API pone en un campo editable que luego vuelve tal cual (la precarga de Componer,
    las celdas de la Hoja): `cifra_escrita(texto_de_cifra(d)) == d` sin perder ni un decimal, de
    modo que «3.000» (tres con tres decimales) nunca regresa como tres mil. Sin exponente; el cero
    negativo se escribe «0». Un `Decimal` no finito es un error de programación (`ValueError`).
    """
    if not valor.is_finite():
        raise ValueError(f"{valor!r} no es un monto finito")
    if valor.is_zero():
        valor = valor.copy_abs()
    fijo = format(valor, "f")
    signo = "-" if fijo.startswith("-") else ""
    entera, _, decimales = fijo.lstrip("-").partition(".")
    grupos = f"{int(entera):,}".replace(",", ".")
    return f"{signo}{grupos}" + (f",{decimales}" if decimales else "")
