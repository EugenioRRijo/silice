"""D3 (tanda de detalles): el texto de la cadena concuerda en singular y plural.

El texto de `core.budget.cadena.mensaje_de_cadena` no se toca (core/ no cambia sin expediente);
`aplicacion.texto_cadena.mensaje_legible` lo corrige para quien lo lee.
"""

import pytest

from aplicacion.texto_cadena import mensaje_legible
from core.budget.cadena import FalloDeCadena, ResultadoCadena


@pytest.mark.parametrize(
    ("versiones", "esperado"),
    [
        (1, "Cadena íntegra: 1 versión"),
        (2, "Cadena íntegra: 2 versiones"),
        (0, "Cadena íntegra: 0 versiones"),
        (11, "Cadena íntegra: 11 versiones"),
    ],
)
def test_cadena_integra_concuerda_en_numero(versiones: int, esperado: str) -> None:
    assert mensaje_legible(ResultadoCadena(True, versiones)) == esperado


def test_cadena_rota_queda_como_la_dice_el_nucleo() -> None:
    fallo = FalloDeCadena("002", "contenido", "x")
    texto = mensaje_legible(ResultadoCadena(False, 2, fallo))
    assert texto.startswith("Cadena rota en la versión 002: su contenido no coincide con su huella")
