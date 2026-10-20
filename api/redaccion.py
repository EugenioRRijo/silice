"""La prosa de los hallazgos que muestran Revisar y Precios de la empresa (VB-16).

Los hallazgos nacen en el nucleo con su texto; aqui solo se ajusta lo que SE MUESTRA: la
concordancia de numero de R11, la lista vacia entre parentesis y la mayuscula inicial de
INDICIO y CUMPLE. No toca el nucleo ni el dato que se guarda.
"""

from __future__ import annotations

import re

__all__ = ["pulir"]

_R11 = re.compile(
    r"^(?P<n>\d+) insumos no contrastables: (?P<a>\d+) sin referencia MaPreX \((?P<la>.*?)\), "
    r"(?P<b>\d+) sin tasa a su fecha \((?P<lb>.*?)\)$"
)


def _r11(m: re.Match[str]) -> str:
    n = int(m["n"])
    grupos = [
        f"{m[cuenta]} {motivo} ({m[lista]})"
        for cuenta, motivo, lista in (
            ("a", "sin referencia MaPreX", "la"),
            ("b", "sin tasa a su fecha", "lb"),
        )
        if int(m[cuenta]) > 0 and m[lista]
    ]
    cabeza = "1 insumo no contrastable" if n == 1 else f"{n} insumos no contrastables"
    return f"{cabeza}: {', '.join(grupos)}" if grupos else cabeza


def pulir(descripcion: str) -> str:
    texto = _R11.sub(_r11, descripcion)
    texto = re.sub(r"\bNO CUMPLE\b", "No cumple", texto)
    texto = re.sub(r"\bCUMPLE\b", "Cumple", texto)
    return re.sub(r"\bINDICIO\b", "Indicio", texto)
