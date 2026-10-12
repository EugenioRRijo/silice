"""Los recorridos guiados de la interfaz (sprint de UI, RF-37 y RF-41).

Datos puros, sin Streamlit.
"""

from __future__ import annotations

import dataclasses

import pytest

from ui.recorridos import (
    NOMBRE_DEMOSTRACION,
    NOMBRE_MONEDA,
    NOMBRE_PRECIOS,
    NOMBRE_PRESUPUESTO,
    RECORRIDOS,
    RUTA_INICIO,
    Paso,
    Recorrido,
    paso_siguiente,
    recorrido_por_nombre,
)

PASO = Paso("Ver el catalogo", "catalogo", "Revise las partidas.", "Ve la tabla de partidas.")
OTRO = Paso("Componer", "componer", "Componga la partida.", "La partida queda guardada.")


def test_hay_cuatro_recorridos_en_el_orden_declarado() -> None:
    assert tuple(r.nombre for r in RECORRIDOS) == (
        NOMBRE_DEMOSTRACION,
        NOMBRE_PRESUPUESTO,
        NOMBRE_PRECIOS,
        NOMBRE_MONEDA,
    )


def test_el_recorrido_de_moneda_pasa_por_las_pantallas_de_s1() -> None:
    recorrido = recorrido_por_nombre(NOMBRE_MONEDA)
    assert [paso.pagina for paso in recorrido.pasos] == [
        "indices",
        "precios_empresa",
        "hoja",
        "reajuste",
    ]


def test_los_recorridos_son_inmutables() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        RECORRIDOS[0].nombre = "otro"  # type: ignore[misc]


def test_ningun_recorrido_pasa_por_el_inicio_ni_repite_pagina() -> None:
    for recorrido in RECORRIDOS:
        paginas = [paso.pagina for paso in recorrido.pasos]
        assert RUTA_INICIO not in paginas, recorrido.nombre
        assert len(set(paginas)) == len(paginas), recorrido.nombre


def test_ningun_texto_de_paso_queda_vacio() -> None:
    for recorrido in RECORRIDOS:
        assert recorrido.proposito.strip()
        for paso in recorrido.pasos:
            assert paso.titulo.strip() and paso.que_hacer.strip() and paso.senal_de_exito.strip()


def test_un_recorrido_sin_pasos_se_rechaza() -> None:
    with pytest.raises(ValueError, match="al menos un paso"):
        Recorrido("vacio", "nada", ())


def test_un_recorrido_que_repite_pagina_se_rechaza() -> None:
    with pytest.raises(ValueError, match="dos veces"):
        Recorrido("doble", "x", (PASO, PASO))


def test_un_recorrido_que_pasa_por_el_inicio_se_rechaza() -> None:
    en_inicio = dataclasses.replace(PASO, pagina=RUTA_INICIO)
    with pytest.raises(ValueError, match="Inicio"):
        Recorrido("inicio", "x", (en_inicio,))


def test_posicion_es_de_base_uno_y_none_fuera_del_recorrido() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert recorrido.posicion("catalogo") == 1
    assert recorrido.posicion("componer") == 2
    assert recorrido.posicion("visor") is None


def test_paso_siguiente_desde_el_inicio_es_el_primero() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert paso_siguiente(recorrido, RUTA_INICIO) == PASO


def test_paso_siguiente_avanza_y_se_detiene_en_el_ultimo() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert paso_siguiente(recorrido, "catalogo") == OTRO
    assert paso_siguiente(recorrido, "componer") is None


def test_una_pantalla_fuera_del_recorrido_no_tiene_paso_siguiente() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert paso_siguiente(recorrido, "visor") is None


def test_sin_recorrido_activo_no_hay_paso_siguiente() -> None:
    assert paso_siguiente(None, RUTA_INICIO) is None
    assert paso_siguiente(None, "catalogo") is None


def test_recorrido_por_nombre() -> None:
    assert recorrido_por_nombre(NOMBRE_PRECIOS) is RECORRIDOS[2]
    assert recorrido_por_nombre(None) is None
    assert recorrido_por_nombre("no existe") is None


# --- SF4: a donde lleva «Recorrido guiado» de la barra (UC-12) ---------------------------------


def test_destino_sin_recorrido_activo_es_el_inicio():
    from ui.recorridos import RUTA_INICIO, destino_de_recorrido

    assert destino_de_recorrido(None, "catalogo") == RUTA_INICIO


def test_destino_es_el_paso_siguiente_desde_un_paso_intermedio():
    from ui.recorridos import RECORRIDOS, destino_de_recorrido

    r = RECORRIDOS[0]
    assert destino_de_recorrido(r, r.pasos[0].pagina) == r.pasos[1].pagina


def test_destino_desde_el_inicio_es_el_primer_paso():
    from ui.recorridos import RECORRIDOS, RUTA_INICIO, destino_de_recorrido

    r = RECORRIDOS[0]
    assert destino_de_recorrido(r, RUTA_INICIO) == r.pasos[0].pagina


def test_destino_desde_una_pantalla_ajena_es_el_primer_paso():
    from ui.recorridos import RECORRIDOS, destino_de_recorrido

    r = RECORRIDOS[0]
    assert destino_de_recorrido(r, "historico") == r.pasos[0].pagina


def test_destino_desde_el_ultimo_paso_es_el_inicio():
    from ui.recorridos import RECORRIDOS, RUTA_INICIO, destino_de_recorrido

    r = RECORRIDOS[0]
    assert destino_de_recorrido(r, r.pasos[-1].pagina) == RUTA_INICIO


def test_el_recorrido_de_presupuesto_termina_en_la_hoja_del_proyecto():
    """RF-37 (enmienda del sprint final): los recorridos incluyen la pantalla «Hoja del proyecto»;
    va despues de Elaborar, que es de donde se abre el resultado (spec §9.1)."""
    r = recorrido_por_nombre(NOMBRE_PRESUPUESTO)
    paginas = [paso.pagina for paso in r.pasos]
    assert paginas == ["catalogo", "componer", "elaborar", "hoja"]
    assert paso_siguiente(r, "elaborar").pagina == "hoja"
    assert paso_siguiente(r, "hoja") is None


def test_algun_recorrido_pasa_por_la_hoja():
    assert any(p.pagina == "hoja" for r in RECORRIDOS for p in r.pasos)
