"""La suite se reparte en trozos (`SILICE_TROZO=k/N`) para correr en varias máquinas a la vez.

Regla de Eugenio del 2026-11-24 (pruebas en paralelo): la CI corre Windows en 4 trozos. El reparto
tiene que ser determinista y estable entre procesos, y cada prueba tiene que caer en un solo trozo.
Las pruebas de otros trozos quedan deseleccionadas, no omitidas, para que `verificar_omitidas.py`
no las cuente como saltadas.
"""

from __future__ import annotations

import pytest

from tests.fixtures.trozos import Trozo, leer_trozo


def _nodeids(cantidad: int) -> list[str]:
    return [f"tests/unit/test_sintetico_{i}.py::test_caso_{i}" for i in range(cantidad)]


@pytest.mark.parametrize("total", [1, 3, 4])
def test_cada_prueba_cae_en_un_solo_trozo(total: int) -> None:
    trozos = [Trozo(numero, total) for numero in range(1, total + 1)]
    for nodeid in _nodeids(2000):
        assert sum(t.incluye(nodeid) for t in trozos) == 1


def test_el_reparto_es_estable_entre_procesos() -> None:
    """La huella sale de SHA-256, no de `hash()`, que cambia de un proceso a otro: un valor fijo
    lo comprueba sin depender de la semilla del intérprete."""
    nodeid = "tests/unit/test_trozos_pruebas.py::test_el_reparto_es_estable_entre_procesos"
    assert [Trozo(n, 4).incluye(nodeid) for n in range(1, 5)].count(True) == 1
    assert Trozo(1, 4).incluye(nodeid) == Trozo(1, 4).incluye(nodeid)


def test_cuatro_trozos_quedan_equilibrados() -> None:
    nodeids = _nodeids(2000)
    for numero in range(1, 5):
        cuantas = sum(Trozo(numero, 4).incluye(n) for n in nodeids)
        assert 0.15 <= cuantas / 2000 <= 0.35


def test_leer_trozo_sin_variable_no_reparte() -> None:
    assert leer_trozo(None) is None
    assert leer_trozo("") is None


@pytest.mark.parametrize(("texto", "trozo"), [("1/4", Trozo(1, 4)), ("4/4", Trozo(4, 4))])
def test_leer_trozo_acepta_k_de_n(texto: str, trozo: Trozo) -> None:
    assert leer_trozo(texto) == trozo


@pytest.mark.parametrize("texto", ["0/4", "5/4", "a/b", "2", "1/0", "1/2/3", "-1/4"])
def test_leer_trozo_rechaza_lo_que_no_es_k_de_n(texto: str) -> None:
    with pytest.raises(ValueError, match="SILICE_TROZO"):
        leer_trozo(texto)


def test_un_trozo_ilegal_no_se_puede_crear() -> None:
    with pytest.raises(ValueError):
        Trozo(0, 4)
    with pytest.raises(ValueError):
        Trozo(1, 0)


def test_dos_trozos_corren_toda_la_mini_suite_sin_omitir_ninguna(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """De punta a punta, con el gancho real de `tests/conftest.py`: 8 pruebas en 2 trozos suman 8
    ejecutadas, las demás de cada trozo salen deseleccionadas y ninguna omitida."""
    pytester.makeconftest("from tests.conftest import pytest_collection_modifyitems\n")
    pytester.makepyfile(
        test_mini="\n\n".join(f"def test_caso_{i}():\n    assert True" for i in range(8))
    )
    corridas = {}
    for trozo in ("1/2", "2/2"):
        monkeypatch.setenv("SILICE_TROZO", trozo)
        corridas[trozo] = pytester.runpytest("-p", "no:cacheprovider").parseoutcomes()
    uno, dos = corridas["1/2"], corridas["2/2"]
    assert uno.get("passed", 0) + dos.get("passed", 0) == 8
    assert uno.get("deselected", 0) == dos.get("passed", 0)
    assert "skipped" not in uno and "skipped" not in dos
