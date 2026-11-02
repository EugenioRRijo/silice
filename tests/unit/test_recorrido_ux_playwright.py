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


def test_cada_ruta_se_lee_del_registro_sin_modulos() -> None:
    """Rediseno del marco, Tarea 8: el registro ya no dice modulo ni area (el marco nuevo los
    reemplaza); el script sigue leyendo id, titulo y accion. Su recorrido por el menu de modulos se
    ajusta al marco nuevo en F7 (plan del rediseno, «Fuera de esta tanda»)."""
    from scripts.recorrido_ux_playwright import rutas_de_la_interfaz

    rutas = {r["id"]: r for r in rutas_de_la_interfaz()}
    # + costos, receta_planta, costo_tonelada y producir_mezcla (plan vial, T2-T6b), tramos (T8) y
    # riesgo (T16)
    assert len(rutas) == 32
    assert "inicio" not in rutas
    assert rutas["hoja"]["titulo"] == "Hoja de la obra"
    # F4 2b (Eugenio, 2026-10-31): quien revisa ve la Hoja en solo lectura; la pantalla pide
    # leer_proyecto y lo que escribe lo decide puedeEditarLaHoja (y la API, editar_hoja).
    assert rutas["hoja"]["accion"] == "leer_proyecto"
    assert rutas["produccion"]["accion"] == "operar_arenera"
    assert rutas["acerca"]["accion"] is None
    assert all(r["modulo"] is None and r["area"] is None for r in rutas.values())


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


# --------------------------- ronda 2 del arbitro de MOD-5a ---------------------------------------


class _Pagina:
    """Pagina falsa: guarda los oyentes de `on` y deja dispararlos a mano."""

    def __init__(self) -> None:
        self.oyentes: dict[str, list] = {}

    def on(self, evento: str, oyente) -> None:  # type: ignore[no-untyped-def]
        self.oyentes.setdefault(evento, []).append(oyente)

    def disparar(self, evento: str, dato: object) -> None:
        for oyente in self.oyentes.get(evento, []):
            oyente(dato)


class _Peticion:
    def __init__(self, metodo: str, url: str) -> None:
        self.method = metodo
        self.url = url
        self.failure = "net::ERR_ABORTED"


class _Respuesta:
    def __init__(self, peticion: _Peticion, estado: int) -> None:
        self.request = peticion
        self.status = estado
        self.url = peticion.url


def test_un_aborto_despues_de_la_respuesta_no_es_fallo_de_red() -> None:
    from scripts.recorrido_ux_playwright import _escuchar

    pagina, consola, red = _Pagina(), [], []
    _escuchar(pagina, consola, red)
    respondida = _Peticion("PUT", "http://127.0.0.1:1/v1/sesion/preferencias")
    pagina.disparar("response", _Respuesta(respondida, 204))
    pagina.disparar("requestfailed", respondida)
    assert red == []
    # Otra peticion a la misma direccion, sin respuesta, si es un fallo.
    sin_respuesta = _Peticion("PUT", "http://127.0.0.1:1/v1/sesion/preferencias")
    pagina.disparar("requestfailed", sin_respuesta)
    assert len(red) == 1 and red[0].startswith("FALLA PUT")
    # Un 500 cuenta aunque llegue respuesta.
    pagina.disparar("response", _Respuesta(_Peticion("GET", "http://127.0.0.1:1/v1/obras"), 500))
    assert red[-1].startswith("500 GET")


def test_umbral_de_la_fila_es_el_mayor_y_sin_una_medida_no_hay_umbral() -> None:
    from scripts.recorrido_ux_playwright import umbral_de_la_fila

    assert umbral_de_la_fila([1500.98, 1663.98, 1204.98]) == pytest.approx(1663.98)
    assert umbral_de_la_fila([1500.98, None]) is None
    assert umbral_de_la_fila([]) is None


def test_umbrales_por_modulo_toman_el_mas_exigente_con_piso_y_marcan_lo_que_falta() -> None:
    from scripts.recorrido_ux_playwright import umbrales_por_modulo

    medidas = [
        {"modulo": "obras", "letra": "normal", "rol": "ana", "carpeta": "a", "umbral": 1500.98},
        {"modulo": "obras", "letra": "normal", "rol": "ana", "carpeta": "b", "umbral": 1663.98},
        {"modulo": "obras", "letra": "normal", "rol": "rita", "carpeta": "a", "umbral": 999.98},
        {"modulo": "auditoria", "letra": "normal", "rol": "ana", "carpeta": "a", "umbral": 999.98},
        {"modulo": "auditoria", "letra": "grande", "rol": "ana", "carpeta": "a", "umbral": 1061.98},
        {"modulo": "auditoria", "letra": "grande", "rol": "rita", "carpeta": "a", "umbral": None},
        {"modulo": "produccion", "letra": "normal", "rol": "ana", "carpeta": "a", "error": "x"},
        {
            "modulo": "produccion",
            "letra": "normal",
            "rol": "admin",
            "carpeta": "a",
            "umbral": 1100.98,
        },
    ]
    salida = umbrales_por_modulo(medidas)
    assert salida["obras"]["normal"] == pytest.approx(1663.98)
    # Piso: Carbon esconde la navegacion de la cabecera por debajo de 1056 px.
    assert salida["auditoria"]["normal"] == pytest.approx(1055.98)
    # Una medida sin umbral (no cabe ni en la ventana mas ancha) o con error no se descarta: deja
    # la casilla sin umbral.
    assert salida["auditoria"]["grande"] is None
    assert salida["produccion"]["normal"] is None


def test_umbrales_sin_medir_nombra_cada_casilla_y_su_causa() -> None:
    from scripts.recorrido_ux_playwright import umbrales_sin_medir

    medidas = [
        {"modulo": "auditoria", "letra": "grande", "rol": "rita", "carpeta": "a", "umbral": None},
        {"modulo": "produccion", "letra": "normal", "rol": "ana", "carpeta": "b", "error": "x"},
        {"modulo": "obras", "letra": "normal", "rol": "ana", "carpeta": "a", "umbral": 1663.98},
    ]
    assert umbrales_sin_medir(medidas) == [
        "auditoria grande (rita, a): no cabe ni en la ventana más ancha",
        "produccion normal (ana, b): error x",
    ]


def test_la_peticion_respondida_se_recuerda_por_referencia_no_por_su_id() -> None:
    # Con `id()` una peticion nueva puede heredar la direccion de una ya liberada y su fallo se
    # perderia; con la referencia guardada eso no pasa.
    import gc

    from scripts.recorrido_ux_playwright import _escuchar

    pagina, consola, red = _Pagina(), [], []
    _escuchar(pagina, consola, red)
    ids = set()
    for _ in range(50):
        vieja = _Peticion("GET", "http://127.0.0.1:1/a")
        ids.add(id(vieja))
        pagina.disparar("response", _Respuesta(vieja, 200))
        del vieja
        gc.collect()
    nuevas = [_Peticion("GET", "http://127.0.0.1:1/b") for _ in range(50)]
    for n in nuevas:
        pagina.disparar("requestfailed", n)
    assert len(red) == 50


def test_barrido_baja_hasta_el_primer_ancho_que_no_cabe_y_afina_de_uno_en_uno() -> None:
    from scripts.recorrido_ux_playwright import barrido, umbral_medido

    medidos: list[int] = []

    def cabe(ancho: int) -> bool:
        medidos.append(ancho)
        return ancho >= 1507

    caben = barrido(cabe, desde=1000, hasta=2600, paso=8)
    assert umbral_medido(caben) == pytest.approx(1506.98)
    # No sigue bajando despues del corte: lo de debajo no cambia el umbral.
    assert min(medidos) >= 1507 - 8
    # Si cabe en todo el tramo, el umbral queda por debajo del menor ancho medido.
    assert umbral_medido(barrido(lambda a: True, desde=1000, hasta=1100, paso=8)) < 1000
    # Los bordes de las consultas de la interfaz (1366 y 1056 px) se miden siempre: un hueco que
    # cae entre dos pasos no se pierde.
    caben = barrido(lambda a: a != 1366, desde=1000, hasta=2600, paso=8)
    assert umbral_medido(caben) == pytest.approx(1366.98)


def test_fallos_del_visor_del_libro() -> None:
    from scripts.recorrido_ux_playwright import fallos_visor

    sano = {
        "axe_libro": ["region"],
        "axe_segunda_hoja": [],
        "errores": [],
        "avisos": ["otro aviso cualquiera"],
        "lienzo": {"ancho": 700, "alto": 500},
        "scroll_x": False,
        "scroll_y": False,
        "vueltas": 2,
    }
    assert fallos_visor(sano) == []
    malo = dict(
        sano,
        axe_segunda_hoja=["aria-valid-attr-value"],
        errores=['pageerror: [redi]: Cannot find "u4" registered by any injector.'],
        avisos=["Univer lanzo al desecharse: Error x"],
        lienzo={"ancho": 0, "alto": 0},
        scroll_x=True,
        vueltas=1,
    )
    fallos = fallos_visor(malo)
    assert any("aria-valid-attr-value" in f for f in fallos)
    assert any("Cannot find" in f for f in fallos)
    # Un aviso de Univer al desecharse significa que D-3 solo quedo escondido.
    assert any("Univer lanzo" in f for f in fallos)
    assert any("lienzo" in f for f in fallos)
    assert any("desplazamiento" in f for f in fallos)
    assert any("vueltas" in f for f in fallos)


def test_contar_por_fase_cuenta_todo_sin_tope() -> None:
    from scripts.recorrido_ux_playwright import contar_por_fase

    textos = ["[abrir] pageerror: x"] * 30 + ["[salir 1] pageerror: y", "[volver 2] z", "sin fase"]
    assert contar_por_fase(textos) == {"abrir": 30, "salir 1": 1, "volver 2": 1, "sin fase": 1}
    assert contar_por_fase([]) == {}


def test_fallos_del_visor_dicen_cuantos_errores_hay_por_fase() -> None:
    from scripts.recorrido_ux_playwright import fallos_visor

    m = {
        "axe_libro": [],
        "axe_segunda_hoja": [],
        "errores": ["[abrir] pageerror: x"] * 12,
        "errores_por_fase": {"abrir": 40, "salir 1": 2},
        "avisos": [],
        "avisos_por_fase": {},
        "lienzo": {"ancho": 700, "alto": 500},
        "vueltas": 2,
    }
    fallos = fallos_visor(m)
    assert "errores por fase: abrir 40, salir 1 2" in fallos


def test_la_tolerancia_de_un_subpixel_vale_para_el_texto_y_para_su_tope() -> None:
    # Chromium redondea a 1/64 px: las dos comparaciones del recorte usan la misma tolerancia.
    from scripts.recorrido_ux_playwright import MOTIVOS_DE_CORTE_JS, TOLERANCIA_SUBPIXEL

    assert TOLERANCIA_SUBPIXEL == 0.05
    assert f"caja - relleno + {TOLERANCIA_SUBPIXEL}" in MOTIVOS_DE_CORTE_JS
    assert f"tope - {TOLERANCIA_SUBPIXEL}" in MOTIVOS_DE_CORTE_JS
    assert "0.01" not in MOTIVOS_DE_CORTE_JS
