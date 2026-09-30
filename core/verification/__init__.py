"""Las siete reglas de verificación (NORMAS.md §7) y el informe de auditoría.

El informe se genera siempre, sin que el usuario lo solicite. Sesión I4.

Uso::

    from core.verification import auditar

    informe = auditar(presupuesto)
    print(informe.a_markdown())

El paquete no importa ningún adaptador ni conoce ningún dominio: todo lo que necesita saber del
caso se lo dice el propio `Presupuesto` (NORMAS.md §2, hipótesis central).
"""

from core.verification import directivas
from core.verification.expresiones import evaluar
from core.verification.informe import InformeAuditoria, auditar
from core.verification.reglas import (
    REGLAS,
    BalanceVolumetrico,
    CierreCurvaInversion,
    CoherenciaDimensional,
    ConciliacionPresupuestoPlan,
    CorrespondenciaEspecificaciones,
    CriterioDepreciacion,
    TrazabilidadGeometrica,
)

__all__ = [
    "REGLAS",
    "BalanceVolumetrico",
    "CierreCurvaInversion",
    "CoherenciaDimensional",
    "ConciliacionPresupuestoPlan",
    "CorrespondenciaEspecificaciones",
    "CriterioDepreciacion",
    "InformeAuditoria",
    "TrazabilidadGeometrica",
    "auditar",
    "directivas",
    "evaluar",
]
