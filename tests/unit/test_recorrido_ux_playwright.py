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
        _fila(letra="grande", letra_aplicada="grande", modo_nav="sidebar", duplicados_nav=2),
        _fila(letra="grande", letra_aplicada="normal", modo_nav="sidebar"),
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
    assert resumen["modo_nav"] == {"barra": 2, "sidebar": 2}
    assert resumen["por_letra"]["normal"]["mediciones"] == 2
    assert resumen["por_letra"]["grande"]["duplicados_nav"] == 2
    assert resumen["con_recorrido"]["mediciones"] == 2
    assert resumen["con_recorrido"]["columna_no_visible"] == 1
    assert resumen["con_recorrido"]["columna_solapa"] == 1


# --------------------------- plan de modulos (MOD-5) -------------------------------------------


def test_cada_ruta_dice_su_modulo_y_su_area() -> None:
    from scripts.recorrido_ux_playwright import rutas_de_la_interfaz

    rutas = {r["id"]: r for r in rutas_de_la_interfaz()}
    # 21 pantallas de antes, los tres inicios y «Estudio de mercado» (plan de modulos, choque 5).
    assert len(rutas) == 25
    assert "inicio" not in rutas
    assert (rutas["auditoria"]["modulo"], rutas["auditoria"]["area"]) == ("auditoria", "inicio")
    assert (rutas["obras"]["modulo"], rutas["obras"]["area"]) == ("obras", "inicio")
    assert (rutas["produccion"]["modulo"], rutas["produccion"]["area"]) == ("produccion", "inicio")
    assert (rutas["mercado"]["modulo"], rutas["mercado"]["area"]) == ("obras", "mercado")
    assert (rutas["revisar"]["modulo"], rutas["revisar"]["area"]) == ("auditoria", "paquetes")
    assert (rutas["existencias"]["modulo"], rutas["existencias"]["area"]) == (
        "produccion",
        "existencias",
    )
    assert (rutas["administracion"]["modulo"], rutas["administracion"]["area"]) == (None, None)
    assert (rutas["acerca"]["modulo"], rutas["acerca"]["area"]) == (None, None)


def test_los_tres_modulos_con_sus_areas_en_orden() -> None:
    from scripts.recorrido_ux_playwright import modulos_de_la_interfaz

    modulos = modulos_de_la_interfaz()
    # Orden y textos de «Restricciones globales» del plan de modulos.
    assert [(m, d["titulo"]) for m, d in modulos.items()] == [
        ("auditoria", "Auditoría"),
        ("obras", "Presupuestos y obras"),
        ("produccion", "Producción"),
    ]
    assert list(modulos["auditoria"]["areas"].values()) == [
        "Inicio",
        "Auditar",
        "Paquetes",
        "Historial",
    ]
    assert list(modulos["obras"]["areas"].values()) == [
        "Inicio",
        "Obras",
        "Partidas",
        "Mercado",
        "Aprobaciones",
        "Control",
    ]
    assert modulos["produccion"]["areas"] == {"inicio": "Inicio", "existencias": "Existencias"}


@pytest.mark.parametrize(
    ("ancho", "letra", "posible"),
    [
        (1366, "normal", True),
        (1365, "normal", False),
        (1056, "normal", False),
        (1707, "grande", False),
        (1708, "grande", True),
        (2048, "muy-grande", False),
        (2049, "muy-grande", True),
        (1366, "grande", False),
    ],
)
def test_fijado_posible_desde_1366_por_la_escala(ancho: int, letra: str, posible: bool) -> None:
    from scripts.recorrido_ux_playwright import fijado_posible

    assert fijado_posible(ancho, letra) is posible


def test_sidebar_esperado_por_estado() -> None:
    from scripts.recorrido_ux_playwright import sidebar_esperado

    assert sidebar_esperado("oculto", 1366, "normal") is None
    assert sidebar_esperado("abierto", 1056, "muy-grande") == "capa"
    assert sidebar_esperado("fijado", 1366, "normal") == "fijado"
    # Sin ancho para fijarlo se comporta como oculto.
    assert sidebar_esperado("fijado", 1056, "normal") is None
    assert sidebar_esperado("fijado", 1366, "grande") is None


def test_sidebars_con_comas_o_espacios_y_desconocido_con_error() -> None:
    from scripts.recorrido_ux_playwright import sidebars_pedidos

    assert sidebars_pedidos(["fijado,oculto"]) == ["oculto", "fijado"]
    assert sidebars_pedidos(["abierto", "oculto"]) == ["oculto", "abierto"]
    with pytest.raises(SystemExit):
        sidebars_pedidos(["capa"])


def test_camino_por_el_menu_de_cada_pantalla() -> None:
    from scripts.recorrido_ux_playwright import camino_por_menu

    assert camino_por_menu("componer") == {
        "modulo": "Presupuestos y obras",
        "area": "Partidas",
        "pantalla": "Componer una partida",
        "inicio": False,
    }
    assert camino_por_menu("auditoria") == {
        "modulo": "Auditoría",
        "area": "Inicio",
        "pantalla": "Inicio de auditoría",
        "inicio": True,
    }
    assert camino_por_menu("acerca") == {
        "modulo": None,
        "area": None,
        "pantalla": "Acerca de Sílice",
        "inicio": False,
    }
    with pytest.raises(ValueError):
        camino_por_menu("inicio")


def test_umbral_medido_es_el_menor_ancho_desde_el_que_siempre_cabe() -> None:
    from scripts.recorrido_ux_playwright import umbral_medido

    # Cabe desde 1290 salvo un hueco en 1366 (aparece el texto de la obra): manda el ultimo hueco.
    caben = {1200: False, 1280: True, 1290: True, 1366: False, 1367: True, 1500: True}
    assert umbral_medido(caben) == pytest.approx(1366.98)
    assert umbral_medido({1000: True, 1100: True}) == pytest.approx(999.98)
    # Si ni el mas ancho cabe, no hay umbral.
    assert umbral_medido({1000: True, 2600: False}) is None


def test_axe_del_inicio_de_antes_pasa_al_inicio_de_auditoria() -> None:
    # «Últimas auditorías» del Inicio de la linea base vive hoy en el inicio de Auditoría.
    fila = _fila(id="auditoria", axe=[{"id": "scrollable-region-focusable"}])
    assert axe_nuevas(fila) == []
    assert axe_nuevas(_fila(id="obras", axe=[{"id": "scrollable-region-focusable"}])) == [
        "scrollable-region-focusable"
    ]


def test_fallo_nav_nombra_el_sidebar_que_tapa_o_que_no_es_el_esperado() -> None:
    linea = fallo_nav(
        _fila(sidebar="fijado", sidebar_modo="fijado", sidebar_esperado="fijado", sidebar_tapa=True)
    )
    assert linea is not None and "tapa" in linea
    linea = fallo_nav(
        _fila(sidebar="fijado", sidebar_modo="fijado", sidebar_esperado=None, sidebar_tapa=False)
    )
    assert linea is not None and "sidebar fijado (se esperaba ninguno)" in linea
    assert fallo_nav(_fila(sidebar="abierto", sidebar_modo="capa", sidebar_esperado="capa")) is None


def test_resumen_por_estado_del_sidebar_y_por_modulo() -> None:
    filas = [
        _fila(sidebar="oculto", modulo="obras"),
        _fila(sidebar="abierto", sidebar_modo="capa", sidebar_esperado="capa", modulo="obras"),
        _fila(
            sidebar="fijado",
            sidebar_modo="fijado",
            sidebar_esperado="fijado",
            sidebar_tapa=True,
            modulo="auditoria",
        ),
        _fila(sidebar="fijado", sidebar_modo=None, sidebar_esperado="fijado", modulo="auditoria"),
    ]
    resumen = resumir(filas)
    assert resumen["sidebar_tapa"] == 1
    assert resumen["sidebar_distinto"] == 1
    assert resumen["por_sidebar"]["fijado"]["mediciones"] == 2
    assert resumen["por_sidebar"]["oculto"]["sidebar_tapa"] == 0
    assert resumen["por_modulo"]["obras"]["mediciones"] == 2


def test_lo_recortado_tambien_en_la_ventana_mas_ancha_no_es_falta_de_espacio() -> None:
    from scripts.recorrido_ux_playwright import motivos_por_espacio

    de_fondo = ["«Ana» recortado a 17 de 29 px"]
    motivos = [
        "«Ana» recortado a 15 de 29 px",
        "«Obra: Torre B» recortado a 20 de 90 px",
        "las áreas se montan sobre el lado derecho",
    ]
    assert motivos_por_espacio(motivos, de_fondo) == motivos[1:]
    assert motivos_por_espacio(de_fondo, de_fondo) == []


def test_el_recorrido_funcional_tiene_una_fila_por_pantalla_y_ninguna_de_mas() -> None:
    from scripts.recorrido_ux_playwright import (
        ACCIONES_TOML,
        cargar_filas_funcionales,
        rutas_de_la_interfaz,
    )

    filas = cargar_filas_funcionales(ACCIONES_TOML)["pantalla"]
    rutas = [f["ruta"] for f in filas]
    assert sorted(rutas) == sorted(r["id"] for r in rutas_de_la_interfaz())
    assert len(rutas) == len(set(rutas))
    # Los tres inicios reemplazan la fila del Inicio de antes (plan de modulos, MOD-5 paso 3).
    assert {"auditoria", "obras", "produccion"} <= set(rutas)
