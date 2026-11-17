"""El único sitio de la API que presenta cifras (plan de desenredo, tarea 2.2).

Cálculo y presentación son cosas distintas (NORMAS.md §2): el núcleo calcula con `Decimal` de 28
dígitos y el redondeo al par del contexto; la API **presenta** a dos decimales con `ROUND_HALF_UP`
(decisión de Eugenio, 2026-11-17), la misma regla que `core.verification.texto.formatear_decimal`.
El contrato sigue con punto decimal: la coma y el punto de miles los pone el navegador
(`frontend-desktop/src/indicadores/formatoEsVe.ts`). Solo `cifra_presentada` escribe con coma, para
los campos que vuelven tal cual (`aplicacion.cifras.texto_de_cifra`).

`tests/unit/test_arquitectura.py::test_la_api_presenta_cifras_en_un_solo_sitio` prohíbe presentar
por su cuenta en el resto de `api/`: un `quantize`, un `ROUND_HALF_*`, un `format(x, "f")` o una
función privada `Decimal -> str` van aquí.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aplicacion.cifras import texto_de_cifra
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal


def _sin_signo_en_cero(texto: str) -> str:
    """`-0.00` -> `0.00` y `-0` -> `0`: una cifra que se presenta como cero no lleva signo."""
    return texto[1:] if texto.startswith("-") and Decimal(texto).is_zero() else texto


def monto(valor: Decimal) -> str:
    """Un monto a dos decimales, al alza: `0.125` -> `0.13`, `-0.001` -> `0.00`. Si no cabe en la
    precisión decimal al cuantizar (más de ~26 cifras enteras), el exacto sin ceros de relleno."""
    try:
        return _sin_signo_en_cero(formatear_decimal(valor, DECIMALES_PRESENTACION))
    except InvalidOperation:
        return exacto_sin_ceros(valor)


def monto_o_nada(valor: Decimal | None) -> str | None:
    return None if valor is None else monto(valor)


def porcentaje(
    parte: Decimal, total: Decimal, decimales: int = DECIMALES_PRESENTACION
) -> str | None:
    """`parte / total * 100` con `decimales` decimales, al alza y sin signo en cero; `None` si el
    total es 0 o si el porcentaje no cabe en la precisión decimal."""
    if total == 0:
        return None
    try:
        return _sin_signo_en_cero(formatear_decimal(parte / total * 100, decimales))
    except InvalidOperation:
        return None


def exacto(valor: Decimal) -> str:
    """El texto decimal tal cual, sin redondear ni recortar ni notación científica."""
    return format(valor, "f")


def exacto_o_nada(valor: Decimal | None) -> str | None:
    return None if valor is None else exacto(valor)


def exacto_sin_ceros(valor: Decimal) -> str:
    """El exacto sin ceros de relleno: `4358.2082500` -> `4358.20825`, `-0.000` -> `0`."""
    return _sin_signo_en_cero(formatear_decimal(valor))


def redondeado(valor: Decimal, lugares: int) -> str:
    """Una cifra que no es un monto, con `lugares` decimales al alza (el FCAS, por ejemplo)."""
    return formatear_decimal(valor, lugares)


def cifra_presentada(valor: Decimal, decimales: int = DECIMALES_PRESENTACION) -> str:
    """La cifra redondeada al alza y escrita con coma decimal y punto de miles: `1234.565` ->
    `1.234,57`."""
    return texto_de_cifra(Decimal(formatear_decimal(valor, decimales)))
