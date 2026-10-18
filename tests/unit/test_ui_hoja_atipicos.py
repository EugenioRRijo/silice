"""El botón «Buscar variaciones atípicas de precio» de la pestaña Precios (RF-100, S3-6).

`AppTest` con la sesión de la hoja y el buscador sustituidos (con `monkeypatch`, que los devuelve
al terminar la prueba): prueba el pegamento. La serie y sus cifras las prueban
`test_series_atipicas.py` y `test_atipicos.py`."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _pagina() -> None:
    from types import SimpleNamespace as N

    from ui.paginas import hoja as pantalla

    pantalla._pintar_atipicos([N(codigo=c) for c in ("MAT-001", "MAT-002", "MAT-003")])


def _sustituir(monkeypatch) -> None:
    from contextlib import contextmanager
    from decimal import Decimal

    import streamlit as st

    from core.contracts.verificacion import Hallazgo, Severidad
    from ui import atipicos
    from ui.paginas import hoja as pantalla

    @contextmanager
    def sin_base():
        # `_sesion()` cede `None` si el caso no existe: la prueba de ese caso lo pide con el estado.
        yield None if st.session_state.get("_sesion_nula") else object()

    dicho = {
        "MAT-001": (
            Hallazgo(
                "ATIPICO",
                Severidad.ADVERTENCIA,
                "MAT-001: variación de 0.39 %",
                valor_observado=Decimal("0.0039"),
            ),
        ),
        "MAT-002": (),
        "MAT-003": (),
    }

    def buscar(sesion, codigos):
        st.session_state["_busquedas"] = st.session_state.get("_busquedas", 0) + 1
        if st.session_state.get("_sin_ml"):
            return None
        sin_tasa = ("Lista en Bs",) if st.session_state.get("_sin_tasa") else ()
        return atipicos.BusquedaAtipicos(
            tuple(h for c in codigos for h in dicho[c]), sin_tasa
        )

    monkeypatch.setattr(pantalla, "_sesion", sin_base)
    monkeypatch.setattr(pantalla.atipicos, "atipicos_de_insumos", buscar)


def _correr(
    monkeypatch,
    sin_ml: bool = False,
    pulsar: bool = True,
    sin_tasa: bool = False,
    sesion_nula: bool = False,
) -> AppTest:
    _sustituir(monkeypatch)
    at = AppTest.from_function(_pagina, default_timeout=60)
    at.session_state["_sin_ml"] = sin_ml
    at.session_state["_sin_tasa"] = sin_tasa
    at.session_state["_sesion_nula"] = sesion_nula
    at = at.run()
    if pulsar:
        at.button(key="hoja_atipicos").click()
        at = at.run()
    return at


def test_sin_pulsar_no_busca_ni_muestra_nada(monkeypatch) -> None:
    at = _correr(monkeypatch, pulsar=False)
    assert not at.warning and not at.success and not at.exception


def test_pulsado_muestra_cada_variacion_atipica_como_advertencia(monkeypatch) -> None:
    at = _correr(monkeypatch)
    assert [w.value for w in at.warning] == ["MAT\\-001: variación de 0\\.39 %"]
    assert not at.error and not at.exception  # nunca ERROR


def test_sin_el_extra_ml_lo_dice_y_no_busca(monkeypatch) -> None:
    at = _correr(monkeypatch, sin_ml=True)
    assert any("extra `ml`" in i.value for i in at.info) and not at.warning


def test_un_precio_en_bs_sin_tasa_se_nombra_al_usuario(monkeypatch) -> None:
    at = _correr(monkeypatch, sin_tasa=True)
    assert [i.value for i in at.info] == ["Precio en Bs sin tasa, omitido: Lista en Bs"]
    assert len(at.warning) == 1  # el hallazgo sigue ahí


def test_si_el_caso_no_se_abre_sale_sin_error_y_sin_buscar(monkeypatch) -> None:
    at = _correr(monkeypatch, sesion_nula=True)
    assert not at.exception and not at.warning and not at.success and not at.info
    assert "_busquedas" not in at.session_state
