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


def test_el_modo_funcional_usa_el_alto_del_portatil_salvo_que_se_pida_otro() -> None:
    # 768 px es el alto del portátil de la empresa; `--alto` sirve para mirar detrás de un defecto
    # que solo se da con ventanas bajas, sin cambiar lo que se mide por omisión.
    assert analizador().parse_args(["--salida", "x", "--funcional"]).alto == 768
    assert analizador().parse_args(["--salida", "x", "--funcional", "--alto", "1080"]).alto == 1080
    with pytest.raises(SystemExit):
        analizador().parse_args(["--salida", "x", "--alto", "0"])


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
    assert len(rutas) == 33  # B1-10: «hoja_pestanas», la vista por pestañas de antes
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


# Sin obra: las 17 pantallas de la obra van a su dirección corta, que el marco lleva a la obra de la
# sesión (contrato §2.4, que se queda tras F8); las demás, a su espacio, a la Cuenta o a Inicio.
RUTAS_SIN_OBRA = {
    "obras": "/obras",
    "tablero": "/tablero",
    "hoja": "/hoja",
    "hoja_pestanas": "/hoja_pestanas",
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
    "hoja_pestanas": "presupuesto/pestanas",
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


# --------------------------- cómo llega una persona (F6, C3-C5, B1-10) ---------------------------
#
# Cada paso: dónde se pulsa («lateral», la barra lateral; «cuenta», el botón de la cuenta de la
# barra de arriba; «barra», una barra de enlaces, con su nombre accesible; «portada», el nombre de
# la obra en su barra, que lleva a la portada; «menu», un menú de botón con su opción) y el texto
# del enlace. «obra» en la barra lateral es la obra elegida para el recorrido, que desde B1-10 abre
# en el Presupuesto (ficha de B1, D1). Dentro de la obra, la barra de dos filas de la cara «Papel y
# resaltador» (especificación 2026-11-26): fila 1, «Herramientas de la obra» (Presupuestar,
# Auditar, Anticipar); fila 2, «Opciones de <herramienta>»; Versiones, en el menú «Versión».

_OBRA = {"donde": "lateral", "nombre": "obra"}
_PRESUPUESTAR = "Opciones de Presupuestar"


def _herramienta(nombre: str) -> dict[str, str]:
    return {"donde": "barra", "barra": "Herramientas de la obra", "nombre": nombre}


def _opcion(barra: str, nombre: str) -> dict[str, str]:
    return {"donde": "barra", "barra": barra, "nombre": nombre}


CAMINOS = {
    "inicio": [{"donde": "lateral", "nombre": "Inicio"}],
    # La obra abre en el Presupuesto: no hace falta otro clic.
    "hoja": [_OBRA],
    "obras": [_OBRA, {"donde": "portada", "nombre": "Portada de la obra"}],
    "tablero": [
        _OBRA,
        {"donde": "portada", "nombre": "Portada de la obra"},
        _opcion("Opciones de la portada", "Tablero"),
    ],
    "componer": [_OBRA, _opcion(_PRESUPUESTAR, "Componer un APU")],
    "hoja_pestanas": [_OBRA, _opcion(_PRESUPUESTAR, "Espacio, plan y ajustes")],
    "tramos": [_OBRA, _opcion(_PRESUPUESTAR, "Tramos de la vía")],
    "archivos": [_OBRA, _opcion(_PRESUPUESTAR, "Plano o cómputo")],
    "mercado": [_OBRA, _opcion(_PRESUPUESTAR, "Precios de mercado")],
    # «Actualizar precios» no es opción de la segunda fila: Mercado conserva su barra de vistas.
    "actualizacion": [
        _OBRA,
        _opcion(_PRESUPUESTAR, "Precios de mercado"),
        _opcion("Vistas de Mercado", "Actualizar precios"),
    ],
    "versiones": [_OBRA, {"donde": "menu", "menu": "Versión", "nombre": "Versiones"}],
    "aprobar": [_OBRA, _herramienta("Auditar")],
    "revisar": [
        _OBRA,
        _herramienta("Auditar"),
        _opcion("Opciones de Auditar", "Revisar un paquete"),
    ],
    "entregar": [_OBRA, _herramienta("Auditar"), _opcion("Opciones de Auditar", "Entregar")],
    "control": [_OBRA, _herramienta("Anticipar")],
    "reajuste": [
        _OBRA,
        _herramienta("Anticipar"),
        _opcion("Opciones de Anticipar", "Reajuste de precios"),
    ],
    "escenarios": [
        _OBRA,
        _herramienta("Anticipar"),
        _opcion("Opciones de Anticipar", "Escenarios"),
    ],
    "riesgo": [_OBRA, _herramienta("Anticipar"), _opcion("Opciones de Anticipar", "Riesgo")],
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
        assert {p["donde"] for p in camino} <= {"lateral", "cuenta", "barra", "portada", "menu"}
        assert not any("Sílice" == p["nombre"] for p in camino), r["id"]
        # La barra de la obra de antes de C4 ya no existe.
        assert not any(p.get("barra") == "Secciones de la obra" for p in camino), r["id"]
    with pytest.raises(ValueError):
        camino_por_el_marco("pendientes")


def test_la_obra_abre_en_el_presupuesto() -> None:
    # B1-10 (D1 de la ficha de B1, 2026-11-26): la barra lateral y el buscador abren la obra en el
    # Presupuesto, la pantalla «hoja».
    from scripts.recorrido_ux_playwright import pagina_de_entrada_de_la_obra, ruta_de_entrada

    assert pagina_de_entrada_de_la_obra() == "hoja"
    assert ruta_de_entrada(("demo.db", 2)) == "#/obra/demo.db/2/presupuesto"
    assert ruta_de_entrada((None, 7)) == "#/obra/empresa/7/presupuesto"


def test_cada_rotulo_que_busca_el_recorrido_esta_escrito_en_su_fuente() -> None:
    # Los nombres accesibles de las barras viven en el JSX, no en una tabla: si alguien los cambia,
    # el recorrido deja de encontrarlos. Esta prueba lo dice antes que el navegador.
    from scripts.recorrido_ux_playwright import RAIZ, ROTULOS_DEL_MARCO

    marco = RAIZ / "frontend-desktop" / "src" / "marco"
    for _clave, (texto, archivo) in ROTULOS_DEL_MARCO.items():
        assert texto in (marco / archivo).read_text(encoding="utf-8"), (texto, archivo)


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


def test_el_texto_de_un_hijo_solo_para_lectores_de_pantalla_no_suma_al_ancho_medido() -> None:
    # Medición responsive del 2026-11-22: con letra grande la etiqueta «Carpeta activa:
    # silice» oculta su rótulo con el mismo patrón (un hijo de 1 px con `clip-path`); el
    # rango de toda la etiqueta sumaba el ancho natural de ese texto oculto y la daba por
    # recortada (42 px de 122) aunque el nombre visible cabía entero. El ancho se mide solo
    # con los nodos de texto que se ven.
    from scripts.recorrido_ux_playwright import BARRAS_JS

    assert "anchoDelTextoVisible" in BARRAS_JS
    assert "NodeFilter.SHOW_TEXT" in BARRAS_JS
    assert "oculto(" in BARRAS_JS


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


# --------------------------- la capa medida de la guardia de interfaz ---------------------------
#
# Norma de interfaz (2026-11-23), «Lo que revisa una persona»: R-8 (8 decisiones o menos a la vista
# por paso) y la primera pantalla (el h1 y el botón principal sin desplazarse a 1366 × 768). Es un
# informe para revisión humana, no una compuerta de la CI: «revisar» es una pregunta, no un fallo.


def _carga(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "fuera_de_tablas": 5,
        "en_tablas": 0,
        "h1_a_la_vista": True,
        "principal_a_la_vista": True,
    }
    base.update(extra)
    return base


def test_una_pantalla_con_pocos_controles_y_todo_a_la_vista_esta_bien() -> None:
    from scripts.recorrido_ux_playwright import veredicto_de_carga

    assert veredicto_de_carga(_carga()) == "bien"
    # Ocho es el umbral aprobado: ocho todavía está bien; nueve ya se revisa.
    assert veredicto_de_carga(_carga(fuera_de_tablas=8)) == "bien"


def test_mas_de_ocho_controles_fuera_de_tablas_se_revisa() -> None:
    from scripts.recorrido_ux_playwright import UMBRAL_DE_DECISIONES, veredicto_de_carga

    assert UMBRAL_DE_DECISIONES == 8
    assert veredicto_de_carga(_carga(fuera_de_tablas=9)) == "revisar"
    assert veredicto_de_carga(_carga(fuera_de_tablas=40)) == "revisar"


def test_los_controles_dentro_de_tablas_y_hojas_no_cuentan_para_el_umbral() -> None:
    # El juez F2: las tablas y las hojas tienen muchos controles por naturaleza.
    from scripts.recorrido_ux_playwright import veredicto_de_carga

    assert veredicto_de_carga(_carga(fuera_de_tablas=3, en_tablas=120)) == "bien"


def test_sin_principal_no_es_falla_si_el_h1_se_ve() -> None:
    from scripts.recorrido_ux_playwright import veredicto_de_carga

    assert veredicto_de_carga(_carga(principal_a_la_vista=None)) == "bien"


@pytest.mark.parametrize(
    "extra",
    [
        {"h1_a_la_vista": False},
        {"principal_a_la_vista": False},
        {"h1_a_la_vista": False, "principal_a_la_vista": None},
    ],
)
def test_un_h1_que_no_se_ve_o_un_principal_fuera_de_la_primera_vista_falla(
    extra: dict[str, object],
) -> None:
    from scripts.recorrido_ux_playwright import veredicto_de_carga

    assert veredicto_de_carga(_carga(**extra)) == "falla"


def test_la_falla_de_la_primera_pantalla_pesa_mas_que_la_revision() -> None:
    from scripts.recorrido_ux_playwright import veredicto_de_carga

    assert veredicto_de_carga(_carga(fuera_de_tablas=20, principal_a_la_vista=False)) == "falla"


def test_la_medida_del_navegador_salta_lo_plegado_lo_cerrado_y_lo_oculto() -> None:
    from scripts.recorrido_ux_playwright import CARGA_JS

    for selector in ("input", "select", "textarea", "button", "[role=combobox]"):
        assert selector in CARGA_JS
    assert "details:not([open])" in CARGA_JS
    assert '[aria-hidden="true"]' in CARGA_JS
    assert "dialog:not([open])" in CARGA_JS
    assert "table, [role=grid]" in CARGA_JS
    assert ".cds--btn--primary" in CARGA_JS
    for clave in ("fuera_de_tablas", "en_tablas", "h1_a_la_vista", "principal_a_la_vista"):
        assert clave in CARGA_JS


def test_la_carga_se_mide_solo_a_1366_con_letra_normal_y_si_se_pide() -> None:
    from scripts.recorrido_ux_playwright import toca_medir_carga

    assert toca_medir_carga(True, 1366, "normal")
    assert not toca_medir_carga(False, 1366, "normal")
    assert not toca_medir_carga(True, 1920, "normal")
    assert not toca_medir_carga(True, 1366, "grande")


def test_la_opcion_medir_carga_existe_y_no_viene_por_omision() -> None:
    assert not analizador().parse_args(["--salida", "x"]).medir_carga
    assert analizador().parse_args(["--salida", "x", "--medir-carga"]).medir_carga


def test_el_informe_de_carga_tiene_una_fila_por_pantalla_con_su_veredicto() -> None:
    from scripts.recorrido_ux_playwright import informe_de_carga

    filas = [
        {"id": "inicio", "titulo": "Vista general", "carga": _carga(fuera_de_tablas=4)},
        {
            "id": "componer",
            "titulo": "Componer",
            "carga": _carga(fuera_de_tablas=31, en_tablas=12, principal_a_la_vista=False),
        },
        {"id": "riesgo", "titulo": "Riesgo", "carga": _carga(fuera_de_tablas=12)},
        {"id": "acerca", "titulo": "Acerca", "carga": _carga(principal_a_la_vista=None)},
        # Medida pedida que no se pudo tomar (la pantalla no cargó): se dice, no se calla.
        {"id": "roto", "titulo": "Rota", "error": "Timeout", "carga": None},
        # Una fila de otro ancho o letra (sin la clave «carga») no entra en la tabla.
        {"id": "otra", "titulo": "Otra"},
    ]
    informe = informe_de_carga(filas)
    lineas = informe.splitlines()
    assert (
        "| Pantalla | Controles fuera de tablas | Controles en tablas | h1 a la vista "
        "| Principal a la vista | Veredicto |"
    ) in lineas
    assert "| Vista general (`inicio`) | 4 | 0 | sí | sí | bien |" in lineas
    assert "| Componer (`componer`) | 31 | 12 | sí | no | falla |" in lineas
    assert "| Riesgo (`riesgo`) | 12 | 0 | sí | sí | revisar |" in lineas
    assert "| Acerca (`acerca`) | 5 | 0 | sí | no hay | bien |" in lineas
    assert "| Rota (`roto`) | — | — | — | — | sin medida |" in lineas
    assert not any("`otra`" in linea for linea in lineas)
    # El resumen cuenta cada veredicto, y el informe dice que «revisar» es una pregunta.
    assert "bien: 2 · revisar: 1 · falla: 1 · sin medida: 1" in informe
    assert "no un cupo" in informe


def test_una_pantalla_que_el_marco_no_ofrece_al_rol_no_lleva_veredicto_de_carga() -> None:
    # Corrida del 2026-11-23 con admin: 20 de las 32 pantallas lo llevan a «Pendientes» o a «Sin
    # permiso», y lo contado ahí no es la pantalla pedida.
    from scripts.recorrido_ux_playwright import informe_de_carga

    filas = [
        {"id": "componer", "titulo": "Componer", "ofrecida": False, "carga": _carga()},
        {"id": "inicio", "titulo": "Vista general", "ofrecida": True, "carga": _carga()},
    ]
    informe = informe_de_carga(filas)
    assert "| Componer (`componer`) | — | — | — | — | no ofrecida al rol |" in informe.splitlines()
    assert "bien: 1 · revisar: 0 · falla: 0 · sin medida: 0 · no ofrecida al rol: 1" in informe


# --------------------------- el marco no se sale de la ventana (2026-11-27) ----------------------


def test_el_marco_quieto_no_es_desborde() -> None:
    from scripts.recorrido_ux_playwright import desborde_del_marco

    marco = {"documento_alto": 768, "ventana_alto": 768, "scroll_y": 0, "marco_scroll": 0}
    assert desborde_del_marco(marco) is None
    # Medio píxel de redondeo no es desborde; sin medida (la página no contestó) tampoco.
    assert desborde_del_marco({**marco, "documento_alto": 769}) is None
    assert desborde_del_marco(None) is None


def test_un_documento_mas_alto_que_la_ventana_o_corrido_es_desborde() -> None:
    # Lo que se vio en reajuste, escenarios y revisar: el documento medía 1123 px en una ventana
    # de 768 y el `focus()` lo había corrido 56 px, con la barra lateral y el contenido corridos.
    from scripts.recorrido_ux_playwright import desborde_del_marco

    marco = {"documento_alto": 1123, "ventana_alto": 768, "scroll_y": 56, "marco_scroll": 0}
    dicho = desborde_del_marco(marco)
    assert dicho is not None
    assert "1123" in dicho
    assert "768" in dicho
    assert "56" in dicho
    assert desborde_del_marco({**marco, "documento_alto": 768, "scroll_y": 0, "marco_scroll": 30})


def test_las_filas_citan_el_rotulo_de_hoy_de_crear_la_obra_y_del_resultado_del_reajuste() -> None:
    # Dos filas fallaban por un texto de antes: «Crear obra» (hoy «Crear la obra») y el resultado
    # del reajuste.
    from scripts.recorrido_ux_playwright import ACCIONES_TOML, RAIZ, cargar_filas_funcionales

    src = RAIZ / "frontend-desktop" / "src"
    filas = {f["ruta"]: f for f in cargar_filas_funcionales(ACCIONES_TOML)["pantalla"]}
    crear = [p["nombre"] for p in filas["obras"]["pasos"] if p["accion"] == "pulsar"][-1]
    assert crear == "Crear la obra"
    assert f'"{crear}"' in (src / "shell" / "obras" / "DialogoNuevaObra.tsx").read_text(
        encoding="utf-8"
    )
    resultado = filas["reajuste"]["espera"]["texto"]
    assert f'"{resultado}"' in (src / "paginas" / "reajuste" / "index.tsx").read_text(
        encoding="utf-8"
    )
