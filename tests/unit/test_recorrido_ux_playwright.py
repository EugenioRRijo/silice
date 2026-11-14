"""Funciones puras de `scripts/recorrido_ux_playwright.py` (sin navegador).

F8, C2: el recorrido ya no navega por el menú de módulos retirado (sidebar «Sílice», áreas de la
barra, selector de obra): recorre los espacios de F6 (barra lateral, barras de cada espacio y la
Cuenta) con las rutas de `marco/espacios.ts` y `marco/secciones.ts`. Los oráculos están escritos a
mano desde el contrato de rutas (docs/especificaciones/2026-11-04-f6a-contrato-de-rutas.md), no
desde el código del marco: si el script lee mal el registro, fallan.
"""

from __future__ import annotations

import pytest

from scripts.recorrido_ux_playwright import (
    analizador,
    anchos_pedidos,
    axe_nuevas,
    camino_por_el_marco,
    fallos_de_la_fila,
    letras_pedidas,
    obra_para,
    resumir,
    sin_nombre,
)


def _fila(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "rol": "ana",
        "ancho": 1366,
        "letra": "normal",
        "letra_aplicada": "normal",
        "id": "inicio",
        "ofrecida": True,
        "h1": 1,
        "scroll_x": False,
        "consola": [],
        "red": [],
        "axe": [],
        "barras": [],
        "controles": [],
    }
    base.update(extra)
    return base


# --------------------------- opciones de la línea de órdenes ------------------------------------


def test_letras_con_comas_o_espacios_en_el_orden_de_la_interfaz() -> None:
    assert letras_pedidas(["muy-grande,normal"]) == ["normal", "muy-grande"]
    assert letras_pedidas(["grande", "normal"]) == ["normal", "grande"]
    assert letras_pedidas(["normal,grande,muy-grande"]) == ["normal", "grande", "muy-grande"]


@pytest.mark.parametrize("valores", [["enorme"], ["normal,enorme"], [","]])
def test_letra_desconocida_o_ninguna_sale_con_error(valores: list[str]) -> None:
    with pytest.raises(SystemExit):
        letras_pedidas(valores)


def test_anchos_con_comas_o_espacios_ordenados_y_sin_repetir() -> None:
    assert anchos_pedidos(["1920,1056", "1366", "1056"]) == [1056, 1366, 1920]


@pytest.mark.parametrize("valores", [["ancho"], ["1366,0"], [","], ["-5"]])
def test_ancho_que_no_es_un_entero_positivo_sale_con_error(valores: list[str]) -> None:
    with pytest.raises(SystemExit):
        anchos_pedidos(valores)


def test_por_omision_mide_los_tres_anchos_de_la_pasada_y_las_tres_letras() -> None:
    args = analizador().parse_args(["--salida", "x"])
    assert anchos_pedidos(args.anchos) == [1056, 1366, 1920]
    assert letras_pedidas(args.letras) == ["normal", "grande", "muy-grande"]
    assert not args.funcional and not args.umbrales


@pytest.mark.parametrize("retirada", ["--sidebar", "--especiales"])
def test_las_opciones_del_menu_de_modulos_ya_no_existen(retirada: str) -> None:
    # `--sidebar` medía el sidebar de módulos y `--especiales`, el selector de obra y el diálogo
    # de carpetas: piezas que el marco de F6 retiró.
    with pytest.raises(SystemExit):
        analizador().parse_args(["--salida", "x", retirada, "oculto"])


# --------------------------- el registro y las rutas de F6 ---------------------------------------


def test_cada_ruta_se_lee_del_registro() -> None:
    from scripts.recorrido_ux_playwright import rutas_de_la_interfaz

    rutas = {r["id"]: r for r in rutas_de_la_interfaz()}
    assert len(rutas) == 32
    assert rutas["inicio"]["titulo"] == "Vista general"
    assert rutas["inicio"]["accion"] is None
    assert rutas["hoja"]["titulo"] == "Presupuesto"
    assert rutas["hoja"]["accion"] == "leer_proyecto"
    assert rutas["produccion"]["accion"] == "operar_arenera"
    assert rutas["acerca"]["accion"] is None
    # El módulo activable de PAGINAS (no el «módulo» del menú retirado).
    assert rutas["tramos"]["modulo"] == "vial"
    assert rutas["riesgo"]["modulo"] == "riesgo"
    assert rutas["hoja"]["modulo"] is None
    assert all("area" not in r for r in rutas.values())


# Sin obra: las 16 pantallas de la obra van a su dirección corta, que el marco lleva a la obra de la
# sesión (contrato §2.4, que se queda tras F8); las demás, a su espacio, a la Cuenta o a Inicio.
RUTAS_SIN_OBRA = {
    "obras": "/obras",
    "tablero": "/tablero",
    "hoja": "/hoja",
    "componer": "/componer",
    "tramos": "/tramos",
    "archivos": "/archivos",
    "versiones": "/versiones",
    "aprobar": "/aprobar",
    "revisar": "/revisar",
    "entregar": "/entregar",
    "mercado": "/mercado",
    "actualizacion": "/actualizacion",
    "control": "/control",
    "reajuste": "/reajuste",
    "escenarios": "/escenarios",
    "riesgo": "/riesgo",
    "produccion": "/produccion/resumen",
    "existencias": "/produccion/existencias",
    "costos": "/produccion/costos",
    "costo_tonelada": "/produccion/costo-tonelada",
    "receta_planta": "/produccion/receta",
    "producir_mezcla": "/produccion/mezcla",
    "auditoria": "/auditoria/subir",
    "libros": "/auditoria/libros",
    "historial": "/auditoria/historial",
    "precios_empresa": "/precios/listas",
    "catalogo": "/precios/catalogo",
    "indices": "/precios/indices",
    "simulador": "/precios/simulador",
    "administracion": "/cuenta/cuentas",
    "acerca": "/cuenta/ayuda",
    "inicio": "/inicio/general",
}

# Con obra (carpeta «demo.db», obra 3): la sección y, si la pantalla es subvista, su segmento.
RUTAS_DE_OBRA = {
    "obras": "resumen",
    "tablero": "resumen/tablero",
    "hoja": "presupuesto",
    "componer": "presupuesto/componer",
    "tramos": "tramos",
    "archivos": "archivos",
    "versiones": "versiones",
    "aprobar": "aprobaciones",
    "revisar": "aprobaciones/revisar",
    "entregar": "aprobaciones/entregar",
    "mercado": "mercado",
    "actualizacion": "mercado/actualizar",
    "control": "control",
    "reajuste": "control/reajuste",
    "escenarios": "control/escenarios",
    "riesgo": "riesgo",
}


def test_cada_pantalla_tiene_su_ruta_canonica_sin_obra() -> None:
    from scripts.recorrido_ux_playwright import ruta_canonica, rutas_de_la_interfaz

    assert {r["id"] for r in rutas_de_la_interfaz()} == set(RUTAS_SIN_OBRA)
    assert {i: ruta_canonica(i) for i in RUTAS_SIN_OBRA} == RUTAS_SIN_OBRA


def test_con_obra_las_pantallas_de_la_obra_van_a_su_seccion_y_subvista() -> None:
    from scripts.recorrido_ux_playwright import ruta_canonica

    obra = ("demo.db", 3)
    for id_, resto in RUTAS_DE_OBRA.items():
        assert ruta_canonica(id_, obra) == f"/obra/demo.db/3/{resto}", id_
    assert ruta_canonica("tablero", (None, 7)) == "/obra/empresa/7/resumen/tablero"
    assert ruta_canonica("libros", obra) == "/auditoria/libros"
    assert ruta_canonica("administracion", obra) == "/cuenta/cuentas"
    assert ruta_canonica("inicio", obra) == "/inicio/general"


def test_una_pantalla_que_no_existe_no_tiene_ruta() -> None:
    from scripts.recorrido_ux_playwright import ruta_canonica

    for id_ in ("pendientes", "elaborar", "historico", ""):
        with pytest.raises(ValueError):
            ruta_canonica(id_)


@pytest.mark.parametrize(
    ("id_", "hash_", "es"),
    [
        ("libros", "#/auditoria/libros", True),
        ("libros", "#/auditoria/libros?x=1", True),
        ("libros", "#/libros", False),
        ("libros", "#/auditoria/librosx", False),
        ("auditoria", "#/auditoria/subir", True),
        ("auditoria", "#/auditoria", False),
        ("costo_tonelada", "#/produccion/costo-tonelada", True),
        ("inicio", "#/inicio/general", True),
        ("inicio", "#/inicio/pendientes", False),
        ("acerca", "#/cuenta/ayuda", True),
        ("hoja", "#/obra/demo.db/3/presupuesto", True),
        ("hoja", "#/obra/empresa/12/presupuesto?proyecto=X", True),
        ("hoja", "#/obra/demo.db/3/presupuesto/componer", False),
        ("componer", "#/obra/demo.db/3/presupuesto/componer", True),
        ("revisar", "#/obra/s1.db/1/aprobaciones/revisar", True),
        ("aprobar", "#/obra/s1.db/1/aprobaciones", True),
        ("aprobar", "#/inicio/pendientes", False),
    ],
)
def test_patron_del_hash_de_cada_pantalla(id_: str, hash_: str, es: bool) -> None:
    import re

    from scripts.recorrido_ux_playwright import patron_de_hash

    assert bool(re.search(patron_de_hash(id_), hash_)) is es


@pytest.mark.parametrize(
    ("enlace", "id_"),
    [
        ("#/auditoria/libros", "libros"),
        ("http://127.0.0.1:1/app/#/produccion/costo-tonelada", "costo_tonelada"),
        ("#/precios/listas?x=1", "precios_empresa"),
        ("#/inicio/general", "inicio"),
        ("#/inicio/pendientes", None),
        ("#/cuenta/cuentas", "administracion"),
        ("#/cuenta/sistema", "administracion"),
        ("#/cuenta/ayuda", "acerca"),
        ("#/cuenta/preferencias", None),
        ("#/obra/demo.db/3/presupuesto", "hoja"),
        ("#/obra/demo.db/3/presupuesto/componer", "componer"),
        ("#/obra/empresa/2/control/escenarios", "escenarios"),
        ("#/obra/empresa/2/riesgo", "riesgo"),
        # La dirección corta de la obra se queda; las de los espacios y la Cuenta se retiraron (C1).
        ("#/hoja", "hoja"),
        ("#/catalogo", None),
        ("#/libros", None),
        ("#/administracion", None),
        ("#/", None),
        ("#/auditoria/nada", None),
    ],
)
def test_la_pantalla_de_cada_enlace(enlace: str, id_: str | None) -> None:
    from scripts.recorrido_ux_playwright import pagina_de_la_ruta

    assert pagina_de_la_ruta(enlace) == id_


# --------------------------- cómo llega una persona (F6) ----------------------------------------
#
# Cada paso: dónde se pulsa («lateral», la barra lateral; «cuenta», el botón de la cuenta de la
# barra de arriba; «barra», una barra de pestañas del espacio, con su nombre accesible) y el texto
# del enlace. «obra» en la barra lateral es la obra elegida para el recorrido.

CAMINOS = {
    "inicio": [{"donde": "lateral", "nombre": "Vista general"}],
    "obras": [{"donde": "lateral", "nombre": "obra"}],
    "hoja": [
        {"donde": "lateral", "nombre": "obra"},
        {"donde": "barra", "barra": "Secciones de la obra", "nombre": "Presupuesto"},
    ],
    "componer": [
        {"donde": "lateral", "nombre": "obra"},
        {"donde": "barra", "barra": "Secciones de la obra", "nombre": "Presupuesto"},
        {"donde": "barra", "barra": "Vistas de Presupuesto", "nombre": "Componer"},
    ],
    "tablero": [
        {"donde": "lateral", "nombre": "obra"},
        {"donde": "barra", "barra": "Vistas de Resumen", "nombre": "Tablero"},
    ],
    "reajuste": [
        {"donde": "lateral", "nombre": "obra"},
        {"donde": "barra", "barra": "Secciones de la obra", "nombre": "Control de obra"},
        {"donde": "barra", "barra": "Vistas de Control de obra", "nombre": "Reajuste"},
    ],
    "riesgo": [
        {"donde": "lateral", "nombre": "obra"},
        {"donde": "barra", "barra": "Secciones de la obra", "nombre": "Riesgo"},
    ],
    "costos": [
        {"donde": "lateral", "nombre": "Costos de producción"},
        {"donde": "barra", "barra": "Costos de producción", "nombre": "Costos del período"},
    ],
    "catalogo": [
        {"donde": "lateral", "nombre": "Precios y catálogo"},
        {
            "donde": "barra",
            "barra": "Precios y catálogo",
            "nombre": "Catálogo de partidas e insumos",
        },
    ],
    "libros": [
        {"donde": "lateral", "nombre": "Auditar un presupuesto"},
        {"donde": "barra", "barra": "Auditar un presupuesto", "nombre": "Libro de la empresa"},
    ],
    "administracion": [
        {"donde": "cuenta", "nombre": "Cuenta"},
        {"donde": "barra", "barra": "Secciones de la cuenta", "nombre": "Cuentas y permisos"},
    ],
    "acerca": [
        {"donde": "cuenta", "nombre": "Cuenta"},
        {
            "donde": "barra",
            "barra": "Secciones de la cuenta",
            "nombre": "Ayuda y acerca de Sílice",
        },
    ],
}


@pytest.mark.parametrize("id_", sorted(CAMINOS))
def test_el_camino_por_el_marco_de_cada_pantalla(id_: str) -> None:
    assert camino_por_el_marco(id_) == CAMINOS[id_]


def test_toda_pantalla_del_registro_tiene_camino_y_ninguno_pasa_por_el_menu_retirado() -> None:
    from scripts.recorrido_ux_playwright import rutas_de_la_interfaz

    for r in rutas_de_la_interfaz():
        camino = camino_por_el_marco(r["id"])
        assert camino, r["id"]
        assert {p["donde"] for p in camino} <= {"lateral", "cuenta", "barra"}, r["id"]
        assert not any("Sílice" == p["nombre"] for p in camino), r["id"]
    with pytest.raises(ValueError):
        camino_por_el_marco("pendientes")


# --------------------------- la obra del recorrido -----------------------------------------------

OBRAS = [
    {"carpeta": None, "obra_id": 1, "obra": "Galpón de la empresa"},
    {"carpeta": "demo.db", "obra_id": 4, "obra": "Sílice: caso de demostracion"},
    {"carpeta": "demo.db", "obra_id": 2, "obra": "Otra de demo"},
    {"carpeta": "obra_control.db", "obra_id": 9, "obra": "OBRA-GENERADA"},
]


def test_la_obra_de_una_fila_por_su_carpeta_y_su_nombre() -> None:
    assert obra_para(OBRAS, "demo.db", "Sílice: caso de demostracion") == OBRAS[1]
    assert obra_para(OBRAS, "obra_control.db", "OBRA-GENERADA") == OBRAS[3]
    # Sin nombre: la primera de la carpeta, en el orden que da el servidor.
    assert obra_para(OBRAS, "demo.db", None) == OBRAS[1]
    # Sin carpeta: la de la empresa.
    assert obra_para(OBRAS, None, None) == OBRAS[0]
    # Como el selector de obra de antes, vale una parte del nombre (las filas dicen «Sílice: caso de
    # demostracion» y la obra de la siembra sigue con «(linea de agua potable, didactico)»); el
    # nombre exacto gana a una coincidencia parcial.
    assert obra_para(OBRAS, "demo.db", "Sílice: caso de") == OBRAS[1]
    assert (
        obra_para(
            OBRAS
            + [
                {"carpeta": "x.db", "obra_id": 5, "obra": "Torre B (anexo)"},
                {"carpeta": "x.db", "obra_id": 6, "obra": "Torre B"},
            ],
            "x.db",
            "Torre B",
        )["obra_id"]
        == 6
    )
    # Un nombre que no está en esa carpeta no se cambia por otra obra.
    assert obra_para(OBRAS, "demo.db", "OBRA-GENERADA") is None
    assert obra_para(OBRAS, "nada.db", None) is None


# --------------------------- controles sin nombre (como axe) -------------------------------------


def test_un_boton_sin_nombre_se_anota_y_lo_oculto_o_invisible_se_salta() -> None:
    controles = [
        {"rol": "button", "nombre": "Guardar", "oculto": False, "visible": True, "html": "<b>"},
        {"rol": "button", "nombre": "", "oculto": False, "visible": True, "html": "<button>"},
        {"rol": "link", "nombre": "  ", "oculto": False, "visible": True, "html": "<a href>"},
        # Dentro de un antepasado aria-hidden="true" (un portal cerrado de Carbon): axe lo salta.
        {"rol": "button", "nombre": "", "oculto": True, "visible": True, "html": "<button x>"},
        {"rol": "button", "nombre": "", "oculto": False, "visible": False, "html": "<button y>"},
    ]
    assert sin_nombre(controles) == ["button <button>", "link <a href>"]
    assert sin_nombre([]) == []


# --------------------------- fallos y resumen ----------------------------------------------------


def test_una_fila_en_verde_no_tiene_fallos() -> None:
    assert fallos_de_la_fila(_fila()) == []


def test_cada_fallo_de_una_fila_se_nombra() -> None:
    fila = _fila(
        h1=0,
        scroll_x=True,
        consola=["pageerror: x"],
        red=["500 GET /v1/obras"],
        axe=[{"id": "label"}],
        controles=[
            {"rol": "button", "nombre": "", "oculto": False, "visible": True, "html": "<i>"}
        ],
        barras=[
            {
                "barra": "Secciones de la obra",
                "desborda": True,
                "fuera": ["Riesgo"],
                "repetidas": [],
            },
            {
                "barra": "Vistas de Control de obra",
                "desborda": False,
                "fuera": [],
                "repetidas": ["X x2"],
            },
        ],
        letra_aplicada="grande",
    )
    fallos = fallos_de_la_fila(fila)
    assert fallos == [
        "sin un h1",
        "desplazamiento horizontal",
        "letra no aplicada (grande en vez de normal)",
        "barra «Secciones de la obra» desborda",
        "barra «Secciones de la obra»: fuera de la ventana Riesgo",
        "barra «Vistas de Control de obra»: repetidas X x2",
        "sin nombre: button <i>",
        "axe nuevas: label",
        "consola: 1",
        "red: 1",
    ]


def test_una_pantalla_que_el_marco_no_ofrece_al_rol_puede_no_tener_h1_propio() -> None:
    # Escrita a mano, dice «Sin permiso» (que sí es un h1); si no lo hay, no es un fallo de diseño
    # de esa pantalla sino del aviso, y se cuenta aparte.
    assert fallos_de_la_fila(_fila(ofrecida=False, h1=0)) == []
    assert fallos_de_la_fila(_fila(error="Timeout")) == ["error: Timeout"]


def test_el_resumen_cuenta_por_letra_y_por_ancho() -> None:
    filas = [
        _fila(),
        _fila(letra="grande", letra_aplicada="grande", scroll_x=True),
        _fila(ancho=1056, h1=0),
        _fila(ancho=1056, ofrecida=False, h1=0),
        _fila(id="libros", recorrido=True, recorrido_visible=False, recorrido_solapa=True),
    ]
    resumen = resumir(filas)
    assert resumen["mediciones"] == 4
    assert resumen["con_fallos"] == 2
    assert resumen["por_letra"]["normal"] == {"mediciones": 3, "con_fallos": 1}
    assert resumen["por_letra"]["grande"] == {"mediciones": 1, "con_fallos": 1}
    assert resumen["por_ancho"]["1056"] == {"mediciones": 2, "con_fallos": 1}
    assert resumen["no_ofrecidas"] == 1
    assert resumen["con_recorrido"] == {
        "mediciones": 1,
        "columna_no_visible": 1,
        "columna_solapa": 1,
    }
    assert resumen["fallos"] == [
        "ana 1366 grande inicio: desplazamiento horizontal",
        "ana 1056 normal inicio: sin un h1",
    ]


def test_axe_solo_cuenta_lo_que_no_estaba_en_la_referencia() -> None:
    fila = _fila(id="administracion", axe=[{"id": "color-contrast"}, {"id": "label"}])
    assert axe_nuevas(fila) == ["label"]
    assert axe_nuevas(_fila(id="hoja", axe=[{"id": "color-contrast"}])) == ["color-contrast"]


def test_axe_del_inicio_de_antes_pasa_al_inicio_de_auditoria() -> None:
    fila = _fila(id="auditoria", axe=[{"id": "scrollable-region-focusable"}])
    assert axe_nuevas(fila) == []
    assert axe_nuevas(_fila(id="obras", axe=[{"id": "scrollable-region-focusable"}])) == [
        "scrollable-region-focusable"
    ]


# --------------------------- umbrales de las barras ----------------------------------------------


def test_umbral_medido_es_el_menor_ancho_desde_el_que_siempre_cabe() -> None:
    from scripts.recorrido_ux_playwright import umbral_medido

    caben = {1200: False, 1280: True, 1290: True, 1366: False, 1367: True, 1500: True}
    assert umbral_medido(caben) == pytest.approx(1366.98)
    assert umbral_medido({1000: True, 1100: True}) == pytest.approx(999.98)
    assert umbral_medido({1000: True, 2600: False}) is None


def test_umbral_de_la_fila_es_el_mayor_y_sin_una_medida_no_hay_umbral() -> None:
    from scripts.recorrido_ux_playwright import umbral_de_la_fila

    assert umbral_de_la_fila([1500.98, 1663.98, 1204.98]) == pytest.approx(1663.98)
    assert umbral_de_la_fila([1500.98, None]) is None
    assert umbral_de_la_fila([]) is None


def test_umbrales_por_lugar_toman_el_mas_exigente_con_piso_y_marcan_lo_que_falta() -> None:
    from scripts.recorrido_ux_playwright import umbrales_por_lugar, umbrales_sin_medir

    medidas = [
        {"lugar": "obra", "letra": "normal", "rol": "ana", "umbral": 1500.98},
        {"lugar": "obra", "letra": "normal", "rol": "rita", "umbral": 1663.98},
        {"lugar": "precios", "letra": "normal", "rol": "ana", "umbral": 999.98},
        {"lugar": "precios", "letra": "grande", "rol": "ana", "umbral": None},
        {"lugar": "cuenta", "letra": "normal", "rol": "admin", "error": "x"},
    ]
    salida = umbrales_por_lugar(medidas)
    assert salida["obra"]["normal"] == pytest.approx(1663.98)
    # Piso: el marco se diseña desde 1056 px (DESIGN.md); por debajo no se mide.
    assert salida["precios"]["normal"] == pytest.approx(1055.98)
    assert salida["precios"]["grande"] is None
    assert salida["cuenta"]["normal"] is None
    assert umbrales_sin_medir(medidas) == [
        "precios grande (ana): no cabe ni en la ventana más ancha",
        "cuenta normal (admin): error x",
    ]


def test_barrido_baja_hasta_el_primer_ancho_que_no_cabe_y_afina_de_uno_en_uno() -> None:
    from scripts.recorrido_ux_playwright import barrido, umbral_medido

    medidos: list[int] = []

    def cabe(ancho: int) -> bool:
        medidos.append(ancho)
        return ancho >= 1507

    caben = barrido(cabe, desde=1000, hasta=2600, paso=8)
    assert umbral_medido(caben) == pytest.approx(1506.98)
    assert min(medidos) >= 1507 - 8
    assert umbral_medido(barrido(lambda a: True, desde=1000, hasta=1100, paso=8)) < 1000
    caben = barrido(lambda a: a != 1366, desde=1000, hasta=2600, paso=8)
    assert umbral_medido(caben) == pytest.approx(1366.98)


def test_lo_recortado_tambien_en_la_ventana_mas_ancha_no_es_falta_de_espacio() -> None:
    from scripts.recorrido_ux_playwright import motivos_por_espacio

    de_fondo = ["«Ana» recortado a 17 de 29 px"]
    motivos = [
        "«Ana» recortado a 15 de 29 px",
        "«Galpón Sur» recortado a 20 de 90 px",
        "barra «Secciones de la obra» desborda",
    ]
    assert motivos_por_espacio(motivos, de_fondo) == motivos[1:]
    assert motivos_por_espacio(de_fondo, de_fondo) == []


def test_la_tolerancia_de_un_subpixel_vale_para_el_texto_y_para_su_tope() -> None:
    from scripts.recorrido_ux_playwright import BARRAS_JS, TOLERANCIA_SUBPIXEL

    assert TOLERANCIA_SUBPIXEL == 0.05
    assert f"caja - relleno + {TOLERANCIA_SUBPIXEL}" in BARRAS_JS
    assert f"tope - {TOLERANCIA_SUBPIXEL}" in BARRAS_JS
    # Las barras del marco de F6, no las del menú de módulos.
    assert "silice-barra-espacio" in BARRAS_JS
    assert "silice-sidebar" not in BARRAS_JS and "Menú principal" not in BARRAS_JS


def test_un_texto_solo_para_lectores_de_pantalla_no_cuenta_como_recortado() -> None:
    # Pasada en navegador de F8 (C3): con letra grande el buscador de la barra de arriba esconde su
    # texto con el patrón «solo para lectores de pantalla» (1 px y `clip-path: inset(50%)`); el
    # detector lo daba por recortado en las 128 mediciones con letra grande o muy grande.
    from scripts.recorrido_ux_playwright import BARRAS_JS

    assert "cs.clipPath !== 'none'" in BARRAS_JS
    assert "caja <= 1" in BARRAS_JS


def test_el_detector_de_controles_salta_lo_aria_hidden() -> None:
    from scripts.recorrido_ux_playwright import CONTROLES_JS

    assert '[aria-hidden="true"]' in CONTROLES_JS


# --------------------------- modo funcional ------------------------------------------------------


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
    assert {"auditoria", "obras", "produccion", "inicio"} <= set(rutas)


def test_las_filas_obras_y_entregar_citan_los_textos_de_hoy() -> None:
    """«Nueva obra» está en la barra lateral (`marco/BarraLateral.tsx`), fuera de <main>; el
    selector de «Entregar paquete» se llama «Obra»
    (`paginas/entregar/index.tsx`, `labelText="Obra"`)."""
    from scripts.recorrido_ux_playwright import ACCIONES_TOML, cargar_filas_funcionales

    filas = {f["ruta"]: f for f in cargar_filas_funcionales(ACCIONES_TOML)["pantalla"]}
    nueva = next(p for p in filas["obras"]["pasos"] if p.get("nombre") == "Nueva obra")
    assert nueva.get("fuera") is True
    selectores = [p for p in filas["entregar"]["pasos"] if p["accion"] == "elegir"]
    assert [p["rotulo"] for p in selectores] == ["Obra"]


PESTANAS_DE_ADMINISTRACION_DE_ANTES = {
    "Cuentas",
    "Empresa y clave de firma",
    "Empresas registradas",
    "Claves de API",
    "Asistente de IA",
    "Accesos",
    "Instalación",
}


def test_las_filas_de_administracion_entran_por_las_secciones_de_la_cuenta() -> None:
    from scripts.recorrido_ux_playwright import ACCIONES_TOML, cargar_filas_funcionales

    filas = cargar_filas_funcionales(ACCIONES_TOML)
    de_admin = [f for tipo in filas.values() for f in tipo if f["ruta"] == "administracion"]
    assert len(de_admin) == 2
    for fila in de_admin:
        for paso in fila.get("pasos", []):
            assert not (
                paso.get("rol") == "tab"
                and paso.get("nombre") in PESTANAS_DE_ADMINISTRACION_DE_ANTES
            ), paso
    siembra = next(f for f in filas["siembra"] if f["ruta"] == "administracion")
    assert siembra["pasos"][0] == {"accion": "pulsar", "rol": "link", "nombre": "Empresa y tema"}


def test_el_archivo_de_filas_ya_no_habla_del_menu_de_modulos() -> None:
    from scripts.recorrido_ux_playwright import ACCIONES_TOML

    texto = ACCIONES_TOML.read_text(encoding="utf-8")
    assert "sidebar" not in texto
    assert "selector de obra" not in texto


# --------------------------- escucha de la red ---------------------------------------------------


class _Pagina:
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
    sin_respuesta = _Peticion("PUT", "http://127.0.0.1:1/v1/sesion/preferencias")
    pagina.disparar("requestfailed", sin_respuesta)
    assert len(red) == 1 and red[0].startswith("FALLA PUT")
    pagina.disparar("response", _Respuesta(_Peticion("GET", "http://127.0.0.1:1/v1/obras"), 500))
    assert red[-1].startswith("500 GET")


def test_la_peticion_respondida_se_recuerda_por_referencia_no_por_su_id() -> None:
    import gc

    from scripts.recorrido_ux_playwright import _escuchar

    pagina, consola, red = _Pagina(), [], []
    _escuchar(pagina, consola, red)
    for _ in range(50):
        vieja = _Peticion("GET", "http://127.0.0.1:1/a")
        pagina.disparar("response", _Respuesta(vieja, 200))
        del vieja
        gc.collect()
    nuevas = [_Peticion("GET", "http://127.0.0.1:1/b") for _ in range(50)]
    for n in nuevas:
        pagina.disparar("requestfailed", n)
    assert len(red) == 50


# --------------------------- visor del libro -----------------------------------------------------


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
    assert "errores por fase: abrir 40, salir 1 2" in fallos_visor(m)
