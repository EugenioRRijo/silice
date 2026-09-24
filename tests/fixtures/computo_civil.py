"""La muestra civil paramétrica (`data/samples/civil/`): códigos, supuestos y factor de la tubería.

Única copia (INV‑009) de lo que comparten las pruebas del adaptador civil:

- Los códigos de partida son los de la línea base, porque el adaptador no decide códigos: los
  recibe el llamador.
- Los cuatro supuestos están declarados en `data/samples/civil/README.md`. La memoria auditada no
  fija margen de excavación, espesor de fondo, diámetro en metros ni desperdicio de tubería.
- El factor de sección de la tubería no se transcribe: se evalúa con la misma expresión que declara
  el adaptador (`adapters.civil.reglas.REGLA_VOLUMEN_TUBERIA`), pero con el evaluador del núcleo
  (`core.verification.expresiones.evaluar`), el mismo con que R1 y R5 comprueban esas cantidades.
  La copia del adaptador (`adapters/civil/evaluador.py`) es una de las cinco de INV‑006.
"""

from __future__ import annotations

from decimal import Decimal

from adapters.civil.reglas import REGLA_VOLUMEN_TUBERIA
from core.verification.expresiones import evaluar
from tests.fixtures import apu_linea_base as linea_base

CODIGOS = {
    "concreto": linea_base.APU_CONCRETO.codigo_partida,
    "encofrado": linea_base.APU_ENCOFRADO.codigo_partida,
    "excavacion": linea_base.APU_EXCAVACION.codigo_partida,
    "tuberia": linea_base.APU_TUBERIA.codigo_partida,
    "relleno": linea_base.APU_RELLENO.codigo_partida,
}

SOBREANCHO = Decimal("0.10")
ESPESOR_FONDO = Decimal("0.10")
DIAMETRO_TUBERIA_M = Decimal("0.1016")  # 4 pulg, coherente con DIAMETRO_TUBERIA_PROYECTO
DESPERDICIO_TUBERIA = Decimal("0.05")

#: Volumen de un metro de tubería de 4 pulg (m3/m): 0,7854 × 0,1016² = 0,008107338624, evaluado
#: con la expresión del adaptador. Antes, la fixture del presupuesto auditado lo escribía truncado
#: a 0,0081 y la prueba del adaptador, completo: dos precisiones del mismo dato.
FACTOR_VOLUMEN_TUBERIA = evaluar(
    REGLA_VOLUMEN_TUBERIA, {"longitud": Decimal("1"), "diametro": DIAMETRO_TUBERIA_M}
)
