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
    # Marco #777777 (L = 0,1845) y el resto neutro (acento #fddc69, lateral #f7f3f2, fondo
    # #f4f4f4); el complementario sigue al marco, así que el botón es #777777. A mano con
    # (L1 + 0,05) / (L2 + 0,05): el blanco sobre el botón en reposo (#777777) 1,05 / 0,2345 = 4,48;
    # al pasar el ratón (85 % con negro: 119 * 0,85 = 101 = #656565, L = 0,130) 1,05 / 0,180 =
    # 5,83; al pulsar (70 %: 83 = #535353, L = 0,0865) 1,05 / 0,1365 = 7,69, que pasa 7:1. Las
    # iniciales (#777777 sobre el acento #fddc69) dan 3,33. El marco como enlace sobre #f4f4f4
    # 4,07, sobre blanco 4,48 y sobre el lateral 4,06; el mismo marco como número del contador
    # sobre el lateral 4,06. La raya de acento (3,33) pasa 3:1.
    assert _con(tmp_path, marco="#777777") == [
        "El texto de la barra superior no se lee bien sobre el color del marco:"
        " 4,4:1, hace falta 4,5:1",
        "El texto de los botones principales no se lee bien sobre su fondo: 4,4:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pasar el ratón:"
        " 5,8:1, hace falta 7:1",
        "Las iniciales de la cuenta no se leen bien sobre el color de acento:"
        " 3,3:1, hace falta 4,5:1",
        "Los enlaces no se leen bien sobre el fondo de la página: 4,0:1, hace falta 4,5:1",
        "Los enlaces no se leen bien sobre las capas blancas: 4,4:1, hace falta 4,5:1",
        "Los enlaces no se leen bien sobre el color lateral: 4,0:1, hace falta 4,5:1",
        "Los bordes de la barra superior casi no se ven sobre el color del marco:"
        " 1,3:1, hace falta 3:1",
        "El número del contador no se lee bien sobre su fondo: 4,0:1, hace falta 4,5:1",
    ]


def test_lateral_oscuro_avisa_del_texto_las_lineas_y_el_contador(tmp_path: Path) -> None:
    # Lateral #1a1a1a (L = 0,0103): el texto #161616 da 1,04; el marco neutro #393939 (L = 0,041)
    # como enlace y como número y contorno del contador da (0,091 / 0,0603) = 1,51 -> «1,5»; el
    # borde #8d8d8d pasa (5,24).
    assert _con(tmp_path, lateral="#1a1a1a") == [
        "Los enlaces no se leen bien sobre el color lateral: 1,5:1, hace falta 4,5:1",
        "El texto del menú lateral no se lee bien sobre el color lateral: 1,0:1, hace falta 4,5:1",
        "El número del contador no se lee bien sobre su fondo: 1,5:1, hace falta 4,5:1",
        "El contorno del contador casi no se ve sobre el color lateral: 1,5:1, hace falta 3:1",
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


def test_complementario_propio_avisa_de_los_enlaces_y_del_boton(tmp_path: Path) -> None:
    # Complementario #767676 con el marco neutro: sobre #f4f4f4 4,13, sobre blanco 4,54 (pasa) y
    # sobre el lateral #f7f3f2 4,12. Es también el botón: el blanco en reposo 4,54, al pasar el
    # ratón (118 * 0,85 = 100 = #646464) 5,92 y al pulsar (#535353) 7,69, que pasa 7:1.
    assert _con(tmp_path, complementario="#767676") == [
        "El texto de los botones principales no se lee bien sobre su fondo: 4,5:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pasar el ratón:"
        " 5,9:1, hace falta 7:1",
        "Los enlaces no se leen bien sobre el fondo de la página: 4,1:1, hace falta 4,5:1",
        "Los enlaces no se leen bien sobre el color lateral: 4,1:1, hace falta 4,5:1",
    ]


def test_complementario_que_solo_falla_en_reposo_da_ese_unico_aviso(tmp_path: Path) -> None:
    # Complementario #1a5fa0 (azul ficticio): el blanco en reposo da 6,586 (< 7); al pasar el ratón
    # (#165188) 8,18 y al pulsar (#124370) 10,18 pasan. Oscurecer sube el contraste con el blanco:
    # si el reposo pasa, los otros dos también; por eso no puede fallar solo el hover.
    assert _con(tmp_path, complementario="#1a5fa0") == [
        "El texto de los botones principales no se lee bien sobre su fondo: 6,5:1, hace falta 7:1",
    ]


def test_complementario_que_falla_reposo_y_hover_pero_no_al_pulsar(tmp_path: Path) -> None:
    # #2a6fa8: reposo 5,333; hover (#245e8f) 6,834; pulsado (#1d4e76) 8,737 (pasa).
    assert _con(tmp_path, complementario="#2a6fa8") == [
        "El texto de los botones principales no se lee bien sobre su fondo: 5,3:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pasar el ratón:"
        " 6,8:1, hace falta 7:1",
    ]


def test_complementario_claro_da_los_tres_avisos_del_boton(tmp_path: Path) -> None:
    # #e0b000: reposo 2,023; hover (#be9600) 2,781; pulsado (#9d7b00) 3,987.
    avisos = _con(tmp_path, complementario="#e0b000")
    assert avisos[:3] == [
        "El texto de los botones principales no se lee bien sobre su fondo: 2,0:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pasar el ratón:"
        " 2,7:1, hace falta 7:1",
        "El texto de los botones principales no se lee bien al pulsarlos: 3,9:1, hace falta 7:1",
    ]


def test_el_borde_del_boton_ya_no_se_mide(tmp_path: Path) -> None:
    # Ni un acento que dejaba el borde del botón en 2,4:1 ni un acento azul dan ya ese aviso, y el
    # aviso de «al pulsarlos» solo sale por un complementario claro, nunca por el acento.
    for acento in ("#ffffff", "#2a6fa8", "#fddc69"):
        avisos = _con(tmp_path, acento=acento)
        assert not any("borde de los botones" in a for a in avisos)
        assert not any("pulsarlos" in a for a in avisos)


def test_iniciales_de_la_cuenta_bajo_4_5_dan_su_aviso(tmp_path: Path) -> None:
    # Acento #2a6fa8 (L = 0,1469) con el marco neutro #393939 (L = 0,0409) en las iniciales:
    # (0,1469 + 0,05) / (0,0409 + 0,05) = 2,17 -> «2,1». La raya de acento (mismo par) da lo mismo
    # contra el 3:1. Acento blanco: 11,55, sin avisos.
    assert _con(tmp_path, acento="#2a6fa8") == [
        "Las iniciales de la cuenta no se leen bien sobre el color de acento:"
        " 2,1:1, hace falta 4,5:1",
        "La raya de color de acento bajo la barra superior casi no se ve sobre el color del marco:"
        " 2,1:1, hace falta 3:1",
    ]
    assert _con(tmp_path, acento="#ffffff") == []


def test_contador_con_poco_contraste_da_dos_avisos(tmp_path: Path) -> None:
    # Número #999999 sobre el fondo #bbbbbb del contador: 1,48; el mismo número (contorno) sobre
    # el lateral neutro #f7f3f2: 2,59 (se muestra «2,5»), por debajo de 3:1; sobre el fondo de la
    # opción activa #e5e0df (L = 0,753) con #999999 (L = 0,3185): 0,803 / 0,3685 = 2,18 («2,1»).
    assert _con(tmp_path, contador_numero="#999999", contador_fondo="#bbbbbb") == [
        "El número del contador no se lee bien sobre su fondo: 1,4:1, hace falta 4,5:1",
        "El contorno del contador casi no se ve sobre el color lateral: 2,5:1, hace falta 3:1",
        "El contorno del contador casi no se ve sobre el fondo de la opción activa del menú"
        " lateral: 2,1:1, hace falta 3:1",
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


def test_la_mezcla_redondea_la_mitad_hacia_arriba_como_el_navegador() -> None:
    # 50 % de #fddc69 con #393939: canal g (220 + 57) / 2 = 138,5 -> 139 (0x8b), no el 138 par que
    # daba round() de Python; r = 155 (0x9b) y b = 81 (0x51) son exactos. Otro empate: 50 % de
    # #050505 con negro = 2,5 -> 3 (round() daba 2).
    assert tema.mezclar("#fddc69", "#393939", 50) == "#9b8b51"
    assert tema.mezclar("#050505", "#000000", 50) == "#030303"


def test_proporciones_del_boton_en_un_solo_sitio() -> None:
    assert tema.OSCURECIDO_DEL_BOTON == {"hover": 85, "pulsado": 70}
    assert not hasattr(tema, "MEZCLAS")


def test_tema_neutro_cumple_los_umbrales_del_boton_con_holgura() -> None:
    # Neutro: botón #393939 (L = 0,0409): el blanco da 1,05 / 0,0909 = 11,55; al pasar el ratón
    # (57 * 0,85 = 48 = #303030) 13,20; al pulsar (#282828) 14,74: los tres sobre 7:1. Las
    # iniciales #393939 sobre el acento #fddc69: 8,59.
    hover = tema.mezclar("#393939", "#000000", 85)
    pulsado = tema.mezclar("#393939", "#000000", 70)
    assert (hover, pulsado) == ("#303030", "#282828")
    assert tema.contraste("#ffffff", "#393939") == pytest.approx(11.55, abs=0.01)
    assert tema.contraste("#ffffff", hover) == pytest.approx(13.20, abs=0.01)
    assert tema.contraste("#ffffff", pulsado) == pytest.approx(14.74, abs=0.01)
    assert tema.contraste("#393939", "#fddc69") == pytest.approx(8.59, abs=0.01)


def test_el_contorno_del_contador_tambien_se_mide_sobre_el_fondo_de_la_opcion_activa(
    tmp_path: Path,
) -> None:
    # La píldora de Pendientes activo queda sobre `lateral-activo` (#e5e0df, L = 0,753). Número
    # #8a8a8a (L = 0,254) sobre el fondo del contador #1a1a1a (L = 0,0103): 5,04, pasa 4,5; sobre
    # el lateral #f7f3f2 (L = 0,903): 3,13, pasa 3:1; pero sobre #e5e0df: (0,753 + 0,05) /
    # (0,254 + 0,05) = 2,64, que se muestra truncado «2,6».
    assert _con(tmp_path, contador_numero="#8a8a8a", contador_fondo="#1a1a1a") == [
        "El contorno del contador casi no se ve sobre el fondo de la opción activa del menú"
        " lateral: 2,6:1, hace falta 3:1"
    ]
