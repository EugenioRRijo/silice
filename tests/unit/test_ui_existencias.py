"""Pantalla «Existencias de la arenera» (Tarea 4.9; UC-28 / UC-29; RT-S4-2, RT-S4-3).

Dos partes:

1. `ui.existencias` (sin Streamlit): el tablero para la pantalla con el estado de cada material y la
   importación de un reporte de báscula con commit y rollback.
2. `ui.paginas.existencias` con `AppTest`: el permiso, la tabla, el registro de un despacho que deja
   la existencia negativa (no se bloquea) y la importación por la pantalla.

Oráculos a mano (ejemplo construido, mínima 20):
* Serie de ARENA: +100 (1/10), −75,5 (2/10) = 24,5 `normal`; −4,5 (3/10) = 20 `queda poco`
  (existencia ≤ mínima); −23 (4/10) = −3 `negativa`.
* `xlsx_basico()` con ARENA (m3, densidad 1,60) y PIEDRA34 (t) y referencia 2026-11-10: se registran
  TCK-001, TCK-002 y TCK-004; van a la bandeja TCK-003 (neto negativo), TCK-005 (fecha futura) y
  TCK-006 (GRAVA9, material desconocido).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest

from adapters.hoja_empresa.guardia import ArchivoRechazado
from produccion.conectores.bascula import ReporteRechazado
from produccion.inventario import (
    crear_material,
    registrar_despacho,
    registrar_entrada,
    tablero,
)
from produccion.modelo import METADATA_PRODUCCION, Movimiento, PesajeSospechoso
from tests.fixtures.bascula.construir import (
    csv_basico,
    xlsx_basico,
    xlsx_con_macros_renombrado,
    xlsx_sin_unidad,
)
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import existencias
from ui import sesion as ui_sesion
from ui.app import paginas_visibles
from ui.existencias import FilaPantalla, importar_desde_pantalla, tablero_para_pantalla
from ui.sesion import MENSAJE_SIN_PERMISO

D = Decimal
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# =================================================================================================
# 1. ui.existencias (sin Streamlit)
# =================================================================================================


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


def _materiales(sesion: Session) -> None:
    crear_material(
        sesion,
        codigo="ARENA",
        nombre="Arena lavada",
        unidad_venta="m3",
        densidad_t_m3=D("1.60"),
        existencia_minima=D("20"),
    )
    crear_material(
        sesion, codigo="PIEDRA34", nombre="Piedra 3/4", unidad_venta="t", existencia_minima=D("10")
    )


def test_tablero_para_pantalla_marca_el_estado(sesion: Session) -> None:
    mid = crear_material(
        sesion, codigo="ARENA", nombre="Arena lavada", unidad_venta="m3", existencia_minima=D("20")
    ).id
    registrar_entrada(sesion, mid, date(2026, 10, 1), D("100"), usuario="p")
    registrar_despacho(sesion, mid, date(2026, 10, 2), D("75.5"), usuario="p")
    registrar_despacho(sesion, mid, date(2026, 10, 3), D("4.5"), usuario="p")
    registrar_despacho(sesion, mid, date(2026, 10, 4), D("23"), usuario="p")

    [normal] = tablero_para_pantalla(sesion, date(2026, 10, 2))
    [poco] = tablero_para_pantalla(sesion, date(2026, 10, 3))
    [negativa] = tablero_para_pantalla(sesion, date(2026, 10, 4))

    assert normal == FilaPantalla("ARENA", "Arena lavada", "m³", "24,5", "20", "normal")
    assert (poco.existencia_texto, poco.estado) == ("20", "queda poco")
    assert (negativa.existencia_texto, negativa.estado) == ("-3", "negativa")


def test_cada_estado_se_rotula_con_icono_y_texto() -> None:
    rotulos = {e: existencias.rotulo_de_estado(e) for e in ("normal", "queda poco", "negativa")}
    assert rotulos["normal"].endswith("Normal")
    assert rotulos["queda poco"].endswith("Queda poco")
    assert rotulos["negativa"].endswith(
        "Existencia negativa: falta registrar producción o conteo"
    )
    # nunca solo color: cada rótulo lleva un signo propio delante del texto
    iconos = {r.split(" ", 1)[0] for r in rotulos.values()}
    assert len(iconos) == 3 and all(len(i) == 1 for i in iconos)


def test_la_cantidad_escrita_acepta_coma_y_rechaza_lo_ambiguo() -> None:
    assert existencias.cantidad_de_texto("24,5", "la entrada") == D("24.5")
    assert existencias.cantidad_de_texto(" 7 ", "la entrada") == D("7")
    for malo in ("", "abc", "1.234,5", "NaN", "Infinity"):
        with pytest.raises(existencias.ErrorDeInventario):
            existencias.cantidad_de_texto(malo, "la entrada")


def test_importar_desde_pantalla_registra_y_manda_lo_dudoso_a_la_bandeja(
    sesion: Session,
) -> None:
    _materiales(sesion)
    sesion.commit()
    resultado = importar_desde_pantalla(
        sesion, xlsx_basico(), "reporte.xlsx", date(2026, 11, 10), None, "ana"
    )
    assert (resultado.registrados, resultado.ya_registrados, resultado.a_la_bandeja) == (3, 0, 3)
    # el commit lo hizo la pantalla: una sesión nueva sobre la misma base ve los despachos
    sesion.expire_all()
    assert len(sesion.scalars(select(Movimiento)).all()) == 3
    assert {s.ticket for s in sesion.scalars(select(PesajeSospechoso))} == {
        "TCK-003",
        "TCK-005",
        "TCK-006",
    }
    assert {m.usuario for m in sesion.scalars(select(Movimiento))} == {"ana"}
    filas = {f.codigo: f for f in tablero_para_pantalla(sesion, date(2026, 11, 10))}
    assert filas["PIEDRA34"].existencia_texto == "-24,5"
    assert filas["PIEDRA34"].estado == "negativa"  # RT-S4-2: el despacho no se bloquea


def test_reimportar_el_mismo_reporte_no_duplica(sesion: Session) -> None:
    _materiales(sesion)
    sesion.commit()
    importar_desde_pantalla(sesion, xlsx_basico(), "r.xlsx", date(2026, 11, 10), None, "ana")
    otra = importar_desde_pantalla(sesion, xlsx_basico(), "r.xlsx", date(2026, 11, 10), None, "ana")
    assert (otra.registrados, otra.ya_registrados, otra.a_la_bandeja) == (0, 3, 0)
    assert len(sesion.scalars(select(Movimiento)).all()) == 3


def test_un_csv_tambien_se_importa(sesion: Session) -> None:
    _materiales(sesion)
    sesion.commit()
    resultado = importar_desde_pantalla(
        sesion, csv_basico(), "r.csv", date(2026, 11, 10), None, "ana"
    )
    assert resultado.registrados == 3


def test_sin_unidad_no_se_importa_nada_y_el_mensaje_es_el_del_lector(sesion: Session) -> None:
    _materiales(sesion)
    sesion.commit()
    with pytest.raises(ReporteRechazado, match="kg o en t"):
        importar_desde_pantalla(
            sesion, xlsx_sin_unidad(), "r.xlsx", date(2026, 11, 10), None, "ana"
        )
    assert sesion.scalars(select(Movimiento)).all() == []
    # indicada la unidad, sí se importa
    ok = importar_desde_pantalla(sesion, xlsx_sin_unidad(), "r.xlsx", date(2026, 11, 10), "kg", "ana")
    assert ok.registrados == 3


def test_un_xlsx_con_macros_renombrado_lo_rechaza_la_guardia(sesion: Session) -> None:
    _materiales(sesion)
    sesion.commit()
    with pytest.raises(ArchivoRechazado):
        importar_desde_pantalla(
            sesion, xlsx_con_macros_renombrado(), "r.xlsx", date(2026, 11, 10), None, "ana"
        )
    assert sesion.scalars(select(Movimiento)).all() == []


# =================================================================================================
# 2. La navegación y la matriz
# =================================================================================================


def test_navegacion_incluye_la_pagina_solo_para_quien_puede() -> None:
    from seguridad.permisos import Rol

    def rutas(*roles: Rol) -> list[str]:
        return [p.ruta_url for p in paginas_visibles(False, frozenset(roles))]

    assert "existencias" in rutas(Rol.ARMA)
    assert "existencias" in rutas(Rol.ADMINISTRADOR)
    assert "existencias" not in rutas(Rol.REVISA)
    assert "existencias" not in rutas()


# =================================================================================================
# 3. La página con AppTest
# =================================================================================================


def _pagina() -> None:
    from ui.paginas import existencias as pagina

    pagina.render()


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


def _abrir(monkeypatch, tmp_path, rol: str = "arma", sembrar: bool = True) -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, rol)
    if sembrar:
        with ui_sesion.instalacion() as bd:
            _materiales(bd)
            bd.commit()
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    return at.run()


def _errores(at: AppTest) -> list[str]:
    return [e.value for e in at.error]


def test_la_pagina_exige_el_permiso(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path, rol="revisa")
    assert not at.exception, [e.value for e in at.exception]
    assert _errores(at) == [MENSAJE_SIN_PERMISO]
    assert not at.dataframe and not at.button and not at.file_uploader


def test_la_pagina_muestra_la_tabla_para_arma(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path)
    assert not at.exception, [e.value for e in at.exception]
    assert not _errores(at)
    assert [t.label for t in at.tabs] == [
        "Existencias",
        "Registrar",
        "Importar báscula",
        "Pesajes sospechosos",
    ]
    tabla = next(d.value for d in at.dataframe if "Estado" in d.value.columns)
    assert list(tabla["Código"]) == ["ARENA", "PIEDRA34"]
    assert set(tabla["Estado"]) == {"▲ Queda poco"}  # existencia 0 ≤ mínima


def test_un_despacho_que_deja_la_existencia_negativa_se_registra_y_se_marca(
    monkeypatch, tmp_path
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    at.selectbox(key="existencias_despacho_material").select("ARENA · Arena lavada")
    at.text_input(key="existencias_despacho_cantidad").set_value("3")
    at.button(key="existencias_despacho_registrar").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not _errores(at)
    tabla = next(d.value for d in at.dataframe if "Estado" in d.value.columns)
    fila = tabla[tabla["Código"] == "ARENA"].iloc[0]
    assert fila["Existencia"] == "-3"
    assert fila["Estado"].endswith("Existencia negativa: falta registrar producción o conteo")
    with ui_sesion.instalacion() as bd:
        [mov] = bd.scalars(select(Movimiento)).all()
        assert (mov.tipo, mov.cantidad) == ("despacho", D("3"))
        assert "luis" in mov.usuario  # el usuario sale de la sesión de la interfaz


def test_un_error_de_inventario_se_dice_sin_traza(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path)
    at.selectbox(key="existencias_entrada_material").select("ARENA · Arena lavada")
    at.text_input(key="existencias_entrada_cantidad").set_value("0")
    at.button(key="existencias_entrada_registrar").click()
    at = at.run()
    assert not at.exception
    assert _errores(at) == ["La cantidad de la entrada debe ser un número mayor que cero."]


def test_importar_por_la_pagina_registra_y_commitea(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path)
    at.file_uploader(key="existencias_archivo").set_value(
        ("reporte.xlsx", xlsx_basico(), MIME_XLSX)
    )
    at = at.run()
    at.button(key="existencias_importar").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not _errores(at)
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Despachos registrados"] == "3"
    assert metricas["A la bandeja de sospechosos"] == "3"
    with ui_sesion.instalacion() as bd:
        assert len(bd.scalars(select(Movimiento)).all()) == 3
        assert len(bd.scalars(select(PesajeSospechoso)).all()) == 3
        assert [f.codigo for f in tablero_para_pantalla(bd, date(2026, 12, 31))] == [
            "ARENA",
            "PIEDRA34",
        ]
        assert tablero(bd)  # el tablero del servicio sigue funcionando


def test_un_archivo_rechazado_dice_por_que(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path)
    at.file_uploader(key="existencias_archivo").set_value(
        ("reporte.xlsx", xlsx_sin_unidad(), MIME_XLSX)
    )
    at = at.run()
    at.button(key="existencias_importar").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("kg o en t" in e for e in _errores(at))


def test_la_bandeja_se_resuelve_desde_la_pagina(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path)
    at.file_uploader(key="existencias_archivo").set_value(
        ("reporte.xlsx", xlsx_basico(), MIME_XLSX)
    )
    at = at.run()
    at.button(key="existencias_importar").click()
    at = at.run()
    # TCK-006 (GRAVA9) se corrige a PIEDRA34 con neto 18,0 t
    opciones = at.selectbox(key="existencias_sospechoso").options
    elegida = next(o for o in opciones if "TCK-006" in o)
    at.selectbox(key="existencias_sospechoso").select(elegida)
    at = at.run()
    at.selectbox(key="existencias_resolver_material").select("PIEDRA34 · Piedra 3/4")
    at.text_input(key="existencias_resolver_neto").set_value("18")
    at.button(key="existencias_resolver").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not _errores(at)
    with ui_sesion.instalacion() as bd:
        assert bd.scalar(select(Movimiento).where(Movimiento.ticket == "TCK-006")) is not None
        estados = {s.ticket: s.estado for s in bd.scalars(select(PesajeSospechoso))}
        assert estados["TCK-006"] == "resuelto"
        assert estados["TCK-003"] == "pendiente"
