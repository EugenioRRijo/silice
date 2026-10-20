"""El piso de `default_timeout` de AppTest vive en un solo lugar (`tests/conftest.py`)."""

from streamlit.testing.v1 import AppTest

from tests.conftest import PISO_TIMEOUT_APPTEST


def _pagina() -> None:
    import streamlit as st

    st.write("hola")


def test_el_piso_aplica_cuando_la_prueba_no_declara_timeout():
    # Streamlit trae 3 s por omision; el piso comun lo sube a 60 s.
    assert AppTest.from_function(_pagina).default_timeout == PISO_TIMEOUT_APPTEST == 60


def test_un_timeout_mayor_declarado_por_la_prueba_se_respeta():
    assert AppTest.from_function(_pagina, default_timeout=120).default_timeout == 120


def test_un_timeout_menor_se_sube_al_piso():
    assert AppTest.from_string("import streamlit", default_timeout=3).default_timeout == 60
