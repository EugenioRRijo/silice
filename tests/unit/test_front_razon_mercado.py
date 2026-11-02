"""La razon «por debajo del piso» que reconoce el front es la del servidor (T15, ronda 2).

La pagina «Estudio de mercado» pinta el icono de aviso de cobro cuando la propuesta trae la razon
`RAZON_POR_DEBAJO` de `aplicacion/mercado.py` (el servidor compara los montos exactos; la pagina no
recalcula la regla). Para eso `frontend-desktop/src/paginas/mercado/logica.ts` repite el texto: si
uno cambia sin el otro, el aviso desaparece en silencio. Esta prueba ata los dos.

Oraculo: la constante del servidor (`aplicacion.mercado.RAZON_POR_DEBAJO`), no el codigo del front.
"""

from __future__ import annotations

import re
from pathlib import Path

from aplicacion.mercado import RAZON_POR_DEBAJO

RAIZ = Path(__file__).resolve().parents[2]
LOGICA = RAIZ / "frontend-desktop" / "src" / "paginas" / "mercado" / "logica.ts"
#: `export const RAZON_POR_DEBAJO = "…";` (una cadena entre comillas dobles, sin comillas dentro).
CONSTANTE = re.compile(r'^export const RAZON_POR_DEBAJO = "([^"\n]*)";$', re.MULTILINE)


def razon_del_front(fuente: str) -> str:
    """El texto de `RAZON_POR_DEBAJO` en el fuente de `logica.ts` (una sola definicion)."""
    halladas = CONSTANTE.findall(fuente)
    assert len(halladas) == 1, f"se esperaba una sola RAZON_POR_DEBAJO; hay {len(halladas)}"
    return halladas[0]


def test_la_razon_por_debajo_del_front_es_la_del_servidor() -> None:
    assert razon_del_front(LOGICA.read_text(encoding="utf-8")) == RAZON_POR_DEBAJO


def test_la_guardia_ve_un_texto_distinto() -> None:
    """Si el front dijera otra cosa (o no la definiera), la comparacion lo nota."""
    otra = 'export const RAZON_POR_DEBAJO = "La competencia cobra menos que su costo.";\n'
    assert razon_del_front(otra) != RAZON_POR_DEBAJO
    try:
        razon_del_front("const otra = 1;\n")
    except AssertionError:
        pass
    else:  # pragma: no cover - solo si la guardia dejara de exigir la definicion
        raise AssertionError("una fuente sin RAZON_POR_DEBAJO debe fallar")
