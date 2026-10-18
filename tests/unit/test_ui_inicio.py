"""La pantalla de Inicio (sprint de UI, RF-36 a RF-40), con `AppTest`.

Arnes heredado de `tests/unit/test_ui_componer.py`: la base se desvia parchando el **objeto
modulo** `sys.modules["ui.caso"]` (no una ruta de texto) y se comprueba antes de pulsar nada que
la desviacion surtio efecto. La salvaguarda de `tests/conftest.py` falla la sesion si algo llega a
`data/apu.db`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ElementList

from operacion.base_datos import Destino, leer_estado, preparar_base, resolver_caso, revision_head
from operacion.config import carpeta_casos
from ui.caso import CLAVE_CASO, CLAVE_RECORRIDO, SIN_PERMISO_DE_CAMBIO, estado_caso
from ui.paginas.inicio import (
    PREFIJO_CASO_ABIERTO,
    ROTULO_ABRIR,
    ROTULO_CASO,
    ROTULO_CREAR,
    ROTULO_NUEVO,
    ROTULO_RECORRIDO,
    ROTULO_SEMBRAR,
)
from ui.recorridos import NOMBRE_PRECIOS, RECORRIDOS

SCRIPT = "from ui.paginas.inicio import render\nrender()\n"

#: La siembra completa (linea base + demostracion + presupuesto auditado) supera holgadamente los
#: 60 s del arnes de la pantalla de componer en una maquina lenta de CI.
TIEMPO_SIEMBRA = 300


def _por_rotulo(elementos: ElementList, rotulo: str):
    for elemento in elementos:
        if elemento.label == rotulo:
            return elemento
    raise AssertionError(f"ningun elemento {rotulo!r}: {[e.label for e in elementos]}")


def _inicio(monkeypatch, base: Path, *, tiempo: int = 60) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=tiempo)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(c.value == f"{PREFIJO_CASO_ABIERTO}{base}" for c in at.caption), (
        "la desviacion de ui.caso.RUTA_BASE_POR_DEFECTO no surtio efecto"
    )
    return at


def _casos(*nombres: str) -> Path:
    carpeta = carpeta_casos()
    for nombre in nombres:
        preparar_base(carpeta / nombre)
    return carpeta


def test_el_inicio_ofrece_los_tres_recorridos(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    radio = _por_rotulo(at.radio, ROTULO_RECORRIDO)
    assert list(radio.options) == [r.nombre for r in RECORRIDOS]
    assert radio.value is None


def test_elegir_un_recorrido_lo_fija_en_la_clave_propia(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.radio, ROTULO_RECORRIDO).set_value(NOMBRE_PRECIOS).run()
    assert at.session_state[CLAVE_RECORRIDO] == NOMBRE_PRECIOS


def test_una_base_inexistente_muestra_el_estado_vacio_sin_crearla(
    monkeypatch, tmp_path: Path
) -> None:
    base = tmp_path / "nueva.db"
    at = _inicio(monkeypatch, base)
    assert any("no tiene partidas" in info.value for info in at.info)
    assert _por_rotulo(at.button, ROTULO_SEMBRAR)
    assert not base.exists()


def test_una_base_existente_sin_partidas_ofrece_sembrar(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "vacia.db"
    base.touch()
    at = _inicio(monkeypatch, base)
    assert any("no tiene partidas" in info.value for info in at.info)
    assert _por_rotulo(at.button, ROTULO_SEMBRAR)


def test_la_siembra_deja_la_base_utilizable(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "nueva.db"
    at = _inicio(monkeypatch, base, tiempo=TIEMPO_SIEMBRA)
    _por_rotulo(at.button, ROTULO_SEMBRAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    estado = estado_caso(base)
    assert estado.partidas > 0 and estado.lista_vigente
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]


def test_con_partidas_no_se_ofrece_sembrar(monkeypatch, tmp_path: Path) -> None:
    from core.catalog import abrir_sesion, crear_esquema, crear_motor
    from scripts.seed import sembrar

    base = tmp_path / "sembrada.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    at = _inicio(monkeypatch, base)
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]


def test_abrir_un_caso_de_la_lista_lo_fija_en_la_clave_propia(monkeypatch, tmp_path: Path) -> None:
    carpeta = _casos("a.db", "b.db")
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    selector = _por_rotulo(at.selectbox, ROTULO_CASO)
    assert list(selector.options) == ["a.db", "b.db"]
    selector.set_value("b.db")
    _por_rotulo(at.button, ROTULO_ABRIR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[CLAVE_CASO] == str(resolver_caso("b.db", carpeta))


def test_el_inicio_no_ofrece_una_ruta_libre(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    assert [campo.label for campo in at.text_input] == [ROTULO_NUEVO]


def test_un_nombre_que_sale_de_la_carpeta_se_rechaza_sin_crear_nada(
    monkeypatch, tmp_path: Path
) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.text_input, ROTULO_NUEVO).set_value("..\\fuera.db")
    _por_rotulo(at.button, ROTULO_CREAR).click().run()
    assert any("sale de la carpeta" in error.value for error in at.error)
    assert CLAVE_CASO not in at.session_state
    assert not (carpeta_casos().parent / "fuera.db").exists()


def test_crear_un_caso_nuevo_lo_deja_en_head_y_abierto(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.text_input, ROTULO_NUEVO).set_value("Obra Ñandú")
    _por_rotulo(at.button, ROTULO_CREAR).click().run()
    ruta = resolver_caso("Obra Ñandú", carpeta_casos())
    assert at.session_state[CLAVE_CASO] == str(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)


def test_sin_permiso_no_se_ofrece_cambiar_de_caso(monkeypatch, tmp_path: Path) -> None:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "puede_cambiar_de_caso", lambda: False)
    _casos("a.db")
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    assert any(SIN_PERMISO_DE_CAMBIO in info.value for info in at.info)
    assert ROTULO_ABRIR not in [boton.label for boton in at.button]
    assert len(at.selectbox) == 0


def test_un_archivo_ilegible_se_informa_sin_ofrecer_sembrar(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "notas.db"
    base.write_text("esto no es una base de datos\n" * 20, encoding="utf-8")
    at = _inicio(monkeypatch, base)
    assert any("No se pudo leer" in error.value for error in at.error)
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]


# --- el libro de Excel, lo primero que se ve ------------------------------------------------------

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_el_inicio_empieza_por_subir_el_libro_de_excel(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    assert at.file_uploader[0].key == "inicio_libro"  # antes que la zona de los casos
    assert not at.get("html")  # sin libro no hay nada que dibujar
    assert [s.value for s in at.subheader][0].startswith("Su libro de Excel")


def test_el_libro_subido_se_dibuja_como_excel_al_instante(monkeypatch, tmp_path: Path) -> None:
    from tests.fixtures.libros_empresa import libro_limpio

    datos = libro_limpio().datos
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    at.file_uploader(key="inicio_libro").set_value(("obra.xlsx", datos, MIME_XLSX))
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    hojas = at.selectbox(key="inicio_hoja").options
    assert hojas[0] == "PORTADA" and "PRESUPUESTO" in hojas
    [html] = [h.proto.body for h in at.get("html")]
    assert "Condominio Ejemplo (ficticio)" in html  # el cliente de la PORTADA del libro
    assert any("Libro de la empresa" in c.value for c in at.caption)
    assert at.session_state["libros_precargado"][0] == "obra.xlsx"


def test_un_archivo_que_no_es_un_libro_se_rechaza_y_no_se_dibuja(monkeypatch, tmp_path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    at.file_uploader(key="inicio_libro").set_value(("obra.xlsx", b"esto no es un ZIP", MIME_XLSX))
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert [e.value for e in at.error] and not at.get("html")
    assert "libros_precargado" not in at.session_state
