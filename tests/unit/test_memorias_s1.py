# tests/unit/test_memorias_s1.py
from pathlib import Path

import pytest

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
LITERALES = {
    "s1_conversion.md": ["1,578869920696521623255111907", "1,162547373805482573414866656",
                         "0,42 USD", "358,11 Bs", "26,37 %", "35,81 %"],
    "s1_reajuste.md": ["1,17", "15 300,00", "16 000,00", "−700,00", "18,00", "18,82", "−0,82"],
    "s1_reajuste_por_partida.md": ["1,175", "1,185", "10 298,34", "11 680,00", "−1 381,66",
                                   "12,12", "13,74", "−1,63", "9 785,88"],
    "s1_precios_empresa.md": ["2026-10-01", "13 377,74", "143 309,00", "1 368,10",
                              "20 521,45", "−20,01 %", "+30,01 %"],
}


@pytest.mark.parametrize("memoria", sorted(LITERALES))
def test_cada_memoria_existe_y_trae_sus_cifras_literales(memoria):
    texto = (MEMORIAS / memoria).read_text(encoding="utf-8")
    faltan = [cifra for cifra in LITERALES[memoria] if cifra not in texto]
    assert not faltan, f"{memoria} no trae {faltan}"
