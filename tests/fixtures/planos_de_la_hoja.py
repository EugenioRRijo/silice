"""Los planos de prueba de la importacion en la hoja (T10, 3e-2): OF-001 y sus variantes.

Lo comparten `test_aplicacion_hoja_planos.py` y `test_api_hoja_plano.py` (INV-052: lo
compartido entre pruebas vive en `tests/fixtures/`). Todo es ficticio: el DXF de OF-001 se dibujo
desde las tablas de la memoria de calculo (`tests/fixtures/planos/README.md`).

Oraculos a mano (de la memoria `tests/fixtures/memorias/of001.md` y de
`tests/unit/test_planos_dxf_of001.py`, nunca del codigo bajo prueba): 6 ambientes, 6 fuentes y 21
puntos importados (33), ninguno sin reconocer; las seis alturas quedan pendientes; los circuitos C1
y C2 entran supuestos (`tests/integration/test_aceptacion_sf.py:251`).
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DXF_OF001 = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
MEMORIA_OF001 = RAIZ / "tests" / "fixtures" / "memorias" / "of001.md"

AMBIENTES_OF001 = ("BAN-01", "COC-01", "CT-01", "REC-01", "ZA", "ZB")
CIRCUITOS_OF001 = ("C1", "C2")
IMPORTADOS_OF001 = 33
#: Las filas que la fusion pone, por tabla (6 ambientes, 6 fuentes, 21 puntos de la memoria).
FILAS_OF001 = {"esp_ambientes": 6, "esp_fuentes": 6, "esp_puntos": 21}
#: Unos bytes que ningun lector reconoce como DXF.
CORRUPTO = b"esto no es un plano DXF\n" * 10


def altura_de_la_memoria() -> str:
    """La altura de los seis ambientes como la teclearia el usuario: la LEE de la memoria de OF-001
    («Todos los ambientes miden 2,500 de alto»), como `_altura_de_la_memoria` del aceptacion SF."""
    coincidencia = re.search(r"miden (\d+,\d+) de alto", MEMORIA_OF001.read_text(encoding="utf-8"))
    assert coincidencia, "la memoria de OF-001 ya no declara la altura de sus ambientes"
    return coincidencia.group(1)


def dxf_sin_unidad(destino: Path) -> Path:
    """El DXF de OF-001 sin `$INSUNITS` (unidad 0): el lector se detiene y pide la unidad."""
    import ezdxf

    documento = ezdxf.readfile(DXF_OF001)
    documento.header["$INSUNITS"] = 0
    documento.saveas(destino)
    return destino
