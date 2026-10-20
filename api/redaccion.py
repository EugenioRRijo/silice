"""La prosa de R11 que muestran Revisar y Precios de la empresa (VB-16).

El hallazgo nace en el nucleo con su texto; aqui solo se ajusta lo que SE MUESTRA: la
concordancia de numero y la lista vacia entre parentesis. Ninguna palabra del usuario (insumo,
partida, empresa) se toca: lo que no calza con la forma exacta de R11 sale intacto, igual que
todo texto de mas de `TOPE` caracteres (el costo es lineal y acotado).
"""

from __future__ import annotations

import re

__all__ = ["TOPE", "pulir"]

#: Por encima de este largo el texto no se analiza: sale intacto.
TOPE = 2000

# Los huecos no cruzan parentesis: no hay retroceso entre dos huecos.
_R11 = re.compile(
    r"(\d+) insumos no contrastables: (\d+) sin referencia MaPreX \(([^()]*)\), "
    r"(\d+) sin tasa a su fecha \(([^()]*)\)"
)


def _r11(m: re.Match[str]) -> str:
    n = int(m[1])
    grupos = [
        f"{cuenta} {motivo}" + (f" ({lista})" if lista else "")
        for cuenta, motivo, lista in (
            (m[2], "sin referencia MaPreX", m[3]),
            (m[4], "sin tasa a su fecha", m[5]),
        )
        if int(cuenta) > 0
    ]
    cabeza = "1 insumo no contrastable" if n == 1 else f"{n} insumos no contrastables"
    return f"{cabeza}: {', '.join(grupos)}" if grupos else cabeza


def pulir(descripcion: str) -> str:
    if len(descripcion) > TOPE:
        return descripcion
    m = _R11.fullmatch(descripcion)
    return _r11(m) if m else descripcion
