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
    # Marco #777777 (L = 0,184) y el resto neutro (acento #fddc69, lateral #f7f3f2, fondo
    # #f4f4f4), a mano con (L1 + 0,05) / (L2 + 0,05): el texto sobre el botón en reposo (#feecac)
    # 3,80; al pasar el ratón (#fde180) 3,47; al pulsar (#fddc69) 3,33; el borde del botón (mezcla
    # 50 % con el marco, #baaa70) sobre el fondo 2,11; el marco como enlace sobre #f4f4f4 4,07,
    # sobre blanco 4,48 y sobre el lateral 4,06; el mismo marco como número del contador sobre el
    # lateral 4,06. La raya de acento (3,33) pasa 3:1.
    assert _con(tmp_path, marco="#777777") == [
        "El texto de la barra superior no se lee bien sobre el color del marco:"
        " 4,4:1, hace falta 4,5:1",
        "El texto de los botones principales no se lee bien sobre su fondo: 3,7:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pasar el ratón:"
        " 3,4:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pulsarlos: 3,3:1, hace falta 7:1",
        "El borde de los botones principales casi no se ve sobre el fondo de la página:"
        " 2,1:1, hace falta 3:1",
        "Los enlaces no se leen bien sobre el fondo de la página: 4,0:1, hace falta 4,5:1",
        "Los enlaces no se leen bien sobre las capas blancas: 4,4:1, hace falta 4,5:1",
        "Los enlaces no se leen bien sobre el color lateral: 4,0:1, hace falta 4,5:1",
        "Los bordes de la barra superior casi no se ven sobre el color del marco:"
        " 1,3:1, hace falta 3:1",
        "El número del contador no se lee bien sobre su fondo: 4,0:1, hace falta 4,5:1",
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
    # #767676 pasa el texto blanco de la barra (4,54:1) pero como enlace sobre #f4f4f4 da 4,13:1.
    avisos = _con(tmp_path, marco="#767676", acento="#ffffff")
    assert (
        "Los enlaces no se leen bien sobre el fondo de la página: 4,1:1, hace falta 4,5:1" in avisos
    )
    assert not any("barra superior no se lee" in a for a in avisos)


def test_complementario_propio_avisa_solo_de_los_enlaces(tmp_path: Path) -> None:
    # Complementario #767676 con el marco neutro: sobre #f4f4f4 4,13, sobre blanco 4,54 (pasa) y
    # sobre el lateral #f7f3f2 4,12. Los bordes interactivos y los enlaces ya no miden el marco,
    # sino este color.
    assert _con(tmp_path, complementario="#767676") == [
        "Los enlaces no se leen bien sobre el fondo de la página: 4,1:1, hace falta 4,5:1",
        "Los enlaces no se leen bien sobre el color lateral: 4,1:1, hace falta 4,5:1",
    ]


def test_acento_azul_da_los_tres_avisos_del_texto_del_boton(tmp_path: Path) -> None:
    # Acento #2a6fa8 con el marco neutro #393939: en reposo (#8ab0cf) 5,06; al pasar el ratón
    # (#4a85b5) 2,92; al pulsar (#2a6fa8) 2,17. El borde (mezcla con el marco, #325470) sobre
    # #f4f4f4 da 7,24 y pasa.
    assert _con(tmp_path, acento="#2a6fa8") == [
        "El texto de los botones principales no se lee bien sobre su fondo: 5,0:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pasar el ratón:"
        " 2,9:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pulsarlos: 2,1:1, hace falta 7:1",
    ]


def test_acento_blanco_avisa_solo_del_borde_del_boton(tmp_path: Path) -> None:
    # Acento #ffffff: el texto #393939 sobre blanco da 11,55 en los tres estados; el borde (50 %
    # con el marco, #9c9c9c) sobre #f4f4f4 da 2,50 (se muestra «2,4»).
    assert _con(tmp_path, acento="#ffffff") == [
        "El borde de los botones principales casi no se ve sobre el fondo de la página:"
        " 2,4:1, hace falta 3:1",
    ]


def test_contador_con_poco_contraste_da_dos_avisos(tmp_path: Path) -> None:
    # Número #999999 sobre el fondo #bbbbbb del contador: 1,48; el mismo número (contorno) sobre
    # el lateral neutro #f7f3f2: 2,59 (se muestra «2,5»), por debajo de 3:1.
    assert _con(tmp_path, contador_numero="#999999", contador_fondo="#bbbbbb") == [
        "El número del contador no se lee bien sobre su fondo: 1,4:1, hace falta 4,5:1",
        "El contorno del contador casi no se ve sobre el color lateral: 2,5:1, hace falta 3:1",
    ]


def test_contador_por_defecto_sigue_al_marco_y_al_lateral(tmp_path: Path) -> None:
    # Sin claves propias, el número es el marco y el fondo es el lateral: un lateral igual al
    # marco se nota también en el contador (1:1).
    avisos = _con(tmp_path, lateral="#393939")
    assert "El número del contador no se lee bien sobre su fondo: 1,0:1, hace falta 4,5:1" in avisos


def test_mezcla_srgb_canal_a_canal() -> None:
    # 55 % de #f1c21b con 45 % de blanco: 241*0,55+255*0,45 = 247,3; 194*0,55+114,75 = 221,45;
    # 27*0,55+114,75 = 129,6 -> #f7dd82. Al 50 % de blanco y negro: 127,5 -> #808080.
    assert tema.mezclar("#f1c21b", "#ffffff", 55) == "#f7dd82"
    assert tema.mezclar("#ffffff", "#000000", 50) == "#808080"
    assert tema.mezclar("#123456", "#abcdef", 100) == "#123456"


def test_proporciones_de_mezcla_en_un_solo_sitio() -> None:
    assert tema.MEZCLAS == {"reposo": 55, "hover": 85, "borde": 50}


def test_tema_neutro_cumple_los_umbrales_del_boton_con_holgura() -> None:
    # Neutro: marco #393939 sobre el botón en reposo #feecac 9,79; al pasar el ratón #fde180 8,94;
    # al pulsar (acento #fddc69) 8,59: los tres sobre 7:1. Borde #9b8a51 sobre #f4f4f4: 3,11.
    reposo = tema.mezclar("#fddc69", "#ffffff", 55)
    sobre = tema.mezclar("#fddc69", "#ffffff", 85)
    borde = tema.mezclar("#fddc69", "#393939", 50)
    assert tema.contraste("#393939", reposo) == pytest.approx(9.79, abs=0.01)
    assert tema.contraste("#393939", sobre) == pytest.approx(8.94, abs=0.01)
    assert tema.contraste("#393939", "#fddc69") == pytest.approx(8.59, abs=0.01)
    assert tema.contraste(borde, "#f4f4f4") == pytest.approx(3.11, abs=0.01)
