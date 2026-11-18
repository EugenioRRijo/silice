"""El corte del control y la fecha de hoy (prueba en vivo del 2026-11-18, frente C, hallazgo 1).

Una valuación con *hasta* futuro hacía que la Vista general y el Resumen midieran el plan en el
futuro («Plan 76,7 %» al 04/12 cuando era el 18/11). Aquí viven las dos compuertas, fuera de los
seis módulos de la fachada `aplicacion.control` (su lista pública está congelada,
`tests/unit/test_arquitectura.py`): el corte que se usa cuando nadie elige uno nunca pasa de hoy y
una valuación del futuro no se registra. La regla R14 del núcleo no se toca. «Hoy» se inyecta para
probar; por defecto, el reloj.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from aplicacion.control_comun import ControlInvalido
from core.budget.valuaciones import valuaciones_registradas

__all__ = ["exigir_que_no_sea_futura", "hoy_o_el_dado", "ultimo_corte"]


def hoy_o_el_dado(hoy: date | None) -> date:
    """`hoy` si se da (las pruebas lo fijan); si no, la fecha del reloj."""
    return date.today() if hoy is None else hoy


def ultimo_corte(sesion: Session, proyecto: str, hoy: date | None = None) -> date | None:
    """El corte que se usa cuando nadie elige uno: el *hasta* de la última valuación no anulada,
    pero **nunca después de hoy** (prueba en vivo del 2026-11-18: una valuación con *hasta* futuro
    medía el plan en el futuro). `None` si no hay valuaciones: quien llama decide qué hacer.

    Una valuación que termina después de hoy no cuenta para el valor ganado (su *hasta* pasa del
    corte) y R14 la señala; la regla es del núcleo y no se toca."""
    hastas = [v.hasta for v in valuaciones_registradas(sesion, proyecto)]
    if not hastas:
        return None
    return min(max(hastas), hoy_o_el_dado(hoy))


def exigir_que_no_sea_futura(hasta: date, fecha: date | None, hoy: date | None = None) -> None:
    """`ControlInvalido` si la valuación termina (`hasta`) o se firma (`fecha`) después de `hoy`.

    Decisión de la prueba en vivo del 2026-11-18: rechazo, no aviso. Una valuación es la medición
    de obra ya ejecutada (UC-19); con un *hasta* futuro, R14 la marca como error al corte y el
    valor ganado no la cuenta, así que guardarla solo deja un error que hay que anular después.
    La regla R14 del núcleo no cambia: esto es una compuerta de la entrada."""
    dia = hoy_o_el_dado(hoy)
    if hasta > dia:
        raise ControlInvalido(
            f"El «Período hasta» ({hasta:%d/%m/%Y}) es posterior a hoy ({dia:%d/%m/%Y}): una "
            "valuación solo mide obra ya ejecutada. Regístrela cuando termine el período."
        )
    if fecha is not None and fecha > dia:
        raise ControlInvalido(
            f"La «Fecha de la valuación» ({fecha:%d/%m/%Y}) es posterior a hoy ({dia:%d/%m/%Y}): "
            "use la fecha en que se firmó, que no puede ser futura."
        )
