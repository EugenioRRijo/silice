"""Contraste del tema de la empresa (rediseño del marco, Tarea 1b): WCAG 2.x, luminancia relativa.

Oráculos a mano o de fuente citada, nunca del propio código:
- WCAG 2.x, definición de «relative luminance» y «contrast ratio» (L1 + 0,05) / (L2 + 0,05).
- #000000 sobre #ffffff = 21:1 (el máximo, W3C); un color sobre sí mismo = 1:1.
- #777777 sobre #ffffff = 4,48:1 (el gris más claro que casi pasa; 4,478 con la fórmula).
- Con marco #777777 y lo demás neutro (Carbon g10), calculados aparte con la misma definición:
  texto blanco sobre #777777 = 4,478; #777777 sobre el acento #f1c21b = 2,660; el borde #8d8d8d
  sobre #777777 = 1,349; el acento sobre #777777 = 2,660. Se muestran truncados a un decimal para
  que un 4,478 nunca se lea «4,5» y parezca pasar.
- Raya del elemento activo del menú lateral (color del marco sobre `lateral-activo`, #e5e0df, de
  luminancia 0,753), a mano con la misma definición: #393939 (neutro) = 8,83:1; #cccccc (L = 0,604)
  = (0,753 + 0,05) / (0,604 + 0,05) = 1,23:1, que se muestra truncado «1,2:1»; #777777
  (L = 0,184) = 3,42:1, que pasa 3:1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aplicacion import tema


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        ("#000000", "#ffffff", 21.0),
        ("#ffffff", "#000000", 21.0),
        ("#ffffff", "#ffffff", 1.0),
        ("#777777", "#ffffff", 4.478),
    ],
)
def test_contraste_wcag(a: str, b: str, esperado: float) -> None:
    assert tema.contraste(a, b) == pytest.approx(esperado, abs=0.005)


def _con(tmp_path: Path, **colores: str) -> list[str]:
    (tmp_path / "tema.json").write_text(json.dumps(colores), encoding="utf-8")
    return tema.leer_tema(tmp_path).avisos


def test_tema_neutro_no_tiene_avisos(tmp_path: Path) -> None:
    assert tema.leer_tema(tmp_path).avisos == []


def test_tema_sin_colores_propios_no_tiene_avisos(tmp_path: Path) -> None:
    assert _con(tmp_path, acento="#xyz") == []


def test_marco_gris_medio_da_los_avisos_exactos(tmp_path: Path) -> None:
    assert _con(tmp_path, marco="#777777") == [
        "El texto de la barra superior no se lee bien sobre el color del marco:"
        " 4,4:1, hace falta 4,5:1",
        "El texto de los botones principales no se lee bien sobre el color de acento:"
        " 2,6:1, hace falta 4,5:1",
        "Los enlaces y bordes del color del marco no se leen bien sobre el fondo de la página:"
        " 4,0:1, hace falta 4,5:1",
        "Los bordes de la barra superior casi no se ven sobre el color del marco:"
        " 1,3:1, hace falta 3:1",
        "La raya de color de acento bajo la barra superior casi no se ve sobre el color del marco: "
        "2,6:1, hace falta 3:1",
    ]


def test_lateral_oscuro_avisa_del_texto_y_las_lineas(tmp_path: Path) -> None:
    # #161616 sobre #1a1a1a: casi 1:1 (el texto); #8d8d8d sobre #1a1a1a pasa 3:1 (5,2:1 a mano).
    assert _con(tmp_path, lateral="#1a1a1a") == [
        "El texto del menú lateral no se lee bien sobre el color lateral: 1,0:1, hace falta 4,5:1",
    ]


def test_colores_que_pasan_no_dan_avisos(tmp_path: Path) -> None:
    # Negro con texto blanco (21:1), acento blanco sobre el marco (21:1), marco negro sobre acento
    # blanco (21:1), lateral blanco con texto #161616 (17,9:1) y borde #8d8d8d (3,3:1 sobre blanco).
    assert _con(tmp_path, marco="#000000", acento="#ffffff", lateral="#ffffff") == []


def test_tema_neutro_cumple_la_raya_del_activo_con_holgura() -> None:
    # #393939 sobre #e5e0df = 8,83:1 a mano (decisión de Eugenio, 2026-10-27: la raya es del marco).
    assert tema.contraste("#393939", "#e5e0df") == pytest.approx(8.83, abs=0.01)
    assert tema.leer_tema(Path("no-existe")).avisos == []


def test_marco_claro_avisa_de_la_raya_del_activo(tmp_path: Path) -> None:
    # El marco #cccccc sobre el fondo del activo da 1,23:1 (a mano): menos de 3:1.
    assert (
        "La raya del elemento activo del menú lateral casi no se ve sobre su fondo:"
        " 1,2:1, hace falta 3:1"
    ) in _con(tmp_path, marco="#cccccc")


def test_marco_gris_medio_no_avisa_de_la_raya_del_activo(tmp_path: Path) -> None:
    # #777777 sobre #e5e0df = 3,42:1 a mano: pasa 3:1, así que la raya no figura entre los avisos.
    assert not any("raya del elemento activo" in a for a in _con(tmp_path, marco="#777777"))



def test_marco_sobre_el_fondo_de_la_pagina_para_enlaces_y_bordes() -> None:
    # El fondo del contenido en Carbon g10 es #f4f4f4 (no blanco). A mano: L(#f4f4f4) = 0,905; el
    # marco neutro #393939 (L = 0,041) da (0,905 + 0,05) / (0,041 + 0,05) = 10,5:1; #777777
    # (L = 0,184) da 4,07:1 (se muestra «4,0»); #767676 (L = 0,181) pasa el texto blanco de la
    # barra (4,54:1) pero sobre #f4f4f4 da 4,13:1, y por eso el par propio hace falta.
    assert tema.contraste("#393939", "#f4f4f4") == pytest.approx(10.5, abs=0.01)
    assert tema.contraste("#767676", "#f4f4f4") == pytest.approx(4.13, abs=0.01)
    assert tema.contraste("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)


def test_marco_justo_para_el_texto_blanco_avisa_de_los_enlaces(tmp_path: Path) -> None:
    avisos = _con(tmp_path, marco="#767676", acento="#ffffff")
    frase = (
        "Los enlaces y bordes del color del marco no se leen bien sobre el fondo de la página:"
        " 4,1:1, hace falta 4,5:1"
    )
    assert frase in avisos
    assert not any("barra superior no se lee" in a for a in avisos)


def test_marco_gris_medio_avisa_de_los_botones_principales(tmp_path: Path) -> None:
    # #777777 sobre #f1c21b: 2,66:1 a mano (ya medido arriba), por debajo de 4,5:1.
    avisos = _con(tmp_path, acento="#f1c21b", marco="#777777")
    assert any(a.startswith("El texto de los botones principales no se lee bien") for a in avisos)
    assert not any("botón Nueva obra" in a for a in avisos)
