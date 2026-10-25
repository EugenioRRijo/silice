"""Funciones puras del modo visual de `scripts/recorrido_ux_playwright.py` (sin navegador)."""

from __future__ import annotations

import pytest

from scripts.recorrido_ux_playwright import axe_nuevas, fallo_nav, letras_pedidas, resumir


def _fila(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "rol": "ana",
        "ancho": 1366,
        "letra": "normal",
        "letra_aplicada": "normal",
        "id": "inicio",
        "en_menu": True,
        "h1": 1,
        "scroll_x": False,
        "consola": [],
        "red": [],
        "axe": [],
        "modo_nav": "barra",
        "duplicados_nav": 0,
        "barra_cortada": False,
        "panel_fuera": False,
    }
    base.update(extra)
    return base


def test_letras_con_comas_o_espacios_en_el_orden_de_la_interfaz() -> None:
    assert letras_pedidas(["muy-grande,normal"]) == ["normal", "muy-grande"]
    assert letras_pedidas(["grande", "normal"]) == ["normal", "grande"]
    assert letras_pedidas(["normal,grande,muy-grande"]) == ["normal", "grande", "muy-grande"]


@pytest.mark.parametrize("valores", [["enorme"], ["normal,enorme"], [","]])
def test_letra_desconocida_o_ninguna_sale_con_error(valores: list[str]) -> None:
    with pytest.raises(SystemExit):
        letras_pedidas(valores)


def test_axe_solo_cuenta_lo_que_no_estaba_en_la_referencia() -> None:
    fila = _fila(
        id="administracion",
        axe=[{"id": "color-contrast"}, {"id": "label"}],
    )
    assert axe_nuevas(fila) == ["label"]
    # La misma regla en otra pantalla sí es nueva.
    assert axe_nuevas(_fila(id="hoja", axe=[{"id": "color-contrast"}])) == ["color-contrast"]


def test_fallo_nav_vacio_si_todo_esta_en_verde() -> None:
    assert fallo_nav(_fila()) is None


def test_fallo_nav_nombra_cada_control_en_rojo() -> None:
    linea = fallo_nav(
        _fila(
            duplicados_nav=1,
            duplicados_detalle={"barra": [], "capa": ["Inicio x2"]},
            panel_fuera=True,
            paneles_fuera=["Más"],
        )
    )
    assert linea is not None
    assert linea.startswith("ana 1366 normal inicio: ")
    assert "Inicio x2" in linea and "Más" in linea and "cortada" not in linea


def test_medicion_sin_controles_de_la_barra_no_pasa_por_verde() -> None:
    fila = _fila(error="Timeout")
    for clave in ("duplicados_nav", "barra_cortada", "panel_fuera"):
        del fila[clave]
    resumen = resumir([fila])
    assert resumen["sin_control_nav"] == 1
    assert resumen["barra_cortada"] == 1
    assert resumen["panel_fuera"] == 1
    assert "sin control de la barra" in resumen["fallos_nav"][0]


def test_resumen_por_letra_y_con_recorrido() -> None:
    filas = [
        _fila(),
        _fila(letra="grande", letra_aplicada="grande", modo_nav="capa", duplicados_nav=2),
        _fila(letra="grande", letra_aplicada="normal", modo_nav="capa"),
        _fila(id="hoja", en_menu=False, h1=0),
        _fila(id="libros", recorrido=True, recorrido_visible=True, recorrido_solapa=False),
        _fila(id="inicio", recorrido=True, recorrido_visible=False, recorrido_solapa=True),
    ]
    resumen = resumir(filas)
    assert resumen["mediciones"] == 4
    assert resumen["en_menu_sin_un_h1"] == 0
    assert resumen["fuera_de_menu_sin_h1"] == 1
    assert resumen["duplicados_nav"] == 2
    assert resumen["letra_no_aplicada"] == 1
    assert resumen["modo_nav"] == {"barra": 2, "capa": 2}
    assert resumen["por_letra"]["normal"]["mediciones"] == 2
    assert resumen["por_letra"]["grande"]["duplicados_nav"] == 2
    assert resumen["con_recorrido"]["mediciones"] == 2
    assert resumen["con_recorrido"]["columna_no_visible"] == 1
    assert resumen["con_recorrido"]["columna_solapa"] == 1
