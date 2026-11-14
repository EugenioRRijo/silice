"""El texto de la cadena de versiones, para quien lo lee (D3 de la tanda de detalles).

`core.budget.cadena.mensaje_de_cadena` dice «1 versiones»; `core/` no cambia sin expediente y aval
del tutor, así que la concordancia se corrige aquí, en la capa que entrega el texto a la API.
"""

from core.budget.cadena import ResultadoCadena, mensaje_de_cadena


def mensaje_legible(resultado: ResultadoCadena) -> str:
    """Como `mensaje_de_cadena`, con «1 versión» en singular."""
    if resultado.integra and resultado.versiones == 1:
        return "Cadena íntegra: 1 versión"
    return mensaje_de_cadena(resultado)
