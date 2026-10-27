"""Contraste del tema de la empresa (rediseño del marco, Tarea 1b): WCAG 2.x, luminancia relativa.

Oráculos a mano o de fuente citada, nunca del propio código:
- WCAG 2.x, definición de «relative luminance» y «contrast ratio» (L1 + 0,05) / (L2 + 0,05).
- #000000 sobre #ffffff = 21:1 (el máximo, W3C); un color sobre sí mismo = 1:1.
- #777777 sobre #ffffff = 4,48:1 (el gris más claro que casi pasa; 4,478 con la fórmula).
- Con marco #777777 y lo demás neutro (Carbon g10), calculados aparte con la misma definición:
  texto blanco sobre #777777 = 4,478; #777777 sobre el acento #f1c21b = 2,660; el borde #8d8d8d
  sobre #777777 = 1,349; el acento sobre #777777 = 2,660. Se muestran truncados a un decimal para
  que un 4,478 nunca se lea «4,5» y parezca pasar.
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
        "El texto del botón Nueva obra no se lee bien sobre el color de acento:"
        " 2,6:1, hace falta 4,5:1",
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
