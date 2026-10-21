"""Reglas de arquitectura de S2 en su propio archivo (RV-2), con los ayudantes compartidos de
`tests/fixtures/arquitectura.py` (sección B, Tarea 1).

* `aplicacion/control.py` (antes `ui/control.py`) no pinta: ni Streamlit, ni `pandas`
  (la misma regla que `PROHIBIDOS_EN_LA_HOJA["aplicacion/hoja.py"]` de `test_arquitectura.py`; un
  módulo de prueba no importa de otro, así que aquí se declara y la prueba lo ata a esa regla por su
  contenido);
* `valor_ganado`, `calendario` y las opciones de recuperación son puras: sin `sqlalchemy` ni
  `core.models`; la decisión, que escribe, vive en `decision.py`;
* `core/verification/valuaciones.py` no importa `core.budget` (la capa de reglas queda debajo);
* ningún módulo de S2 emite `UPDATE` ni `DELETE` sobre las tablas solo-agregar (S2-R10);
* ninguna pantalla de S2 importa `scripts` ni `tests` al cargar (RV-25) ni usa HTML sin escapar
  (RV-14).
"""

from __future__ import annotations

import re

import pytest

from tests.fixtures.arquitectura import RAIZ, importaciones

PROHIBIDOS_EN_CONTROL = ("streamlit", "pandas")
PUROS = (
    "core/budget/valor_ganado.py",
    "core/budget/calendario.py",
    "core/budget/recuperacion.py",
)
SOLO_AGREGAR = (
    "core/budget/valuaciones.py",
    "core/budget/puente.py",
    "core/budget/decision.py",
)
PAGINAS_DE_S2 = ("aplicacion/control.py",)  # `ui/paginas/control.py` se fue con Streamlit (F4)


def _coincide(modulo: str, prefijo: str) -> bool:
    return modulo == prefijo or modulo.startswith(prefijo + ".")


def test_control_no_pinta_ni_lee_la_sesion_de_streamlit():
    prohibidos = {
        modulo
        for modulo in importaciones(RAIZ / "aplicacion" / "control.py")
        for prefijo in PROHIBIDOS_EN_CONTROL
        if _coincide(modulo, prefijo)
    }
    assert prohibidos == set()


def test_la_regla_de_control_es_la_misma_que_la_de_la_hoja():
    """Si cambia la regla de `aplicacion/hoja.py`, se revisa la de `aplicacion/control.py`."""
    texto = (RAIZ / "tests" / "unit" / "test_arquitectura.py").read_text(encoding="utf-8")
    regla = re.search(r'"aplicacion/hoja\.py": \(([^)]*)\)', texto)
    assert regla is not None
    assert tuple(re.findall(r'"([^"]+)"', regla.group(1))) == PROHIBIDOS_EN_CONTROL


@pytest.mark.parametrize("modulo", PUROS)
def test_los_calculos_de_s2_son_puros_sin_base_de_datos(modulo):
    prohibidos = {
        m
        for m in importaciones(RAIZ / modulo)
        if _coincide(m, "sqlalchemy") or _coincide(m, "core.models") or _coincide(m, "core.catalog")
    }
    assert prohibidos == set()


def test_las_reglas_r13_y_r14_no_dependen_de_la_capa_de_presupuesto():
    importados = importaciones(RAIZ / "core" / "verification" / "valuaciones.py")
    assert {m for m in importados if _coincide(m, "core.budget")} == set()
    assert {m for m in importados if _coincide(m, "sqlalchemy")} == set()


@pytest.mark.parametrize("modulo", SOLO_AGREGAR)
def test_ningun_modulo_de_s2_borra_ni_actualiza_las_tablas_solo_agregar(modulo):
    texto = (RAIZ / modulo).read_text(encoding="utf-8")
    assert not re.search(r"\.delete\(|\bdelete\(|\bupdate\(|\.update\(", texto)
    assert "from sqlalchemy import" not in texto or not re.search(
        r"from sqlalchemy import[^\n]*\b(delete|update)\b", texto
    )


@pytest.mark.parametrize("modulo", PAGINAS_DE_S2)
def test_las_pantallas_de_s2_no_importan_scripts_ni_tests_ni_usan_html_sin_escapar(modulo):
    texto = (RAIZ / modulo).read_text(encoding="utf-8")
    assert "unsafe_allow_html" not in texto
    assert not {m for m in importaciones(RAIZ / modulo) if m.split(".")[0] in ("scripts", "tests")}


def test_ningun_contrato_importa_nada_de_s2():
    for archivo in sorted((RAIZ / "core" / "contracts").glob("*.py")):
        assert not {
            m for m in importaciones(archivo) if _coincide(m, "core.budget") or "valuaciones" in m
        }, archivo.name
