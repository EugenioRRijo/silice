"""UC-06 4a (INV-093) en la pantalla «Componer una partida» (fase C6).

Con la advertencia de RF-27 a la vista, la pantalla ofrece el campo «Justificacion de la
advertencia (UC-06, flujo 4a)» y, al guardar, registra la justificacion ligada al rendimiento que
ese guardado acaba de registrar (`core.catalog.justificar_rendimiento`). Sin advertencia no hay
campo ni justificacion. Si el guardado no registro un rendimiento nuevo, la pantalla no justifica
y lo avisa: el ultimo rendimiento de la partida seria otro y la justificacion se ligaria en
silencio al equivocado (hallazgo 1 de la revision de requisitos de N y N-5 de la de arquitectura).

Caso didactico (CLAUDE.md §1): la tuberia `LB-02-TUB` de la linea base, sembrada por
`scripts.seed.sembrar` con rendimiento 100, mas un segundo rendimiento estimado de 110 registrado
por el nucleo directo. Aritmetica a mano del oraculo: dos observaciones, rango [100, 110];
teclear 150 queda fuera del rango (advierte) y 105 dentro (no advierte). El arnes es el de
`tests/unit/test_ui_componer.py` (AppTest, base desviada parchando el objeto modulo `ui.caso` y la
ayuda 1 sustituida por un doble); cada base vive en `tmp_path` y se vigila la huella de
`data/apu.db`.
"""

from __future__ import annotations

import importlib
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor, registrar_rendimiento
from core.contracts import TipoRendimiento
from ml.normalization import Propuesta
from scripts.seed import sembrar
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures.apu_linea_base import APU_TUBERIA, FECHA_LINEA_BASE
from ui.composicion import desglose
from ui.elaboracion import Guardado

SCRIPT = "from ui.paginas.componer import render\nrender()\n"
ROTULO_JUSTIFICACION = "Justificacion de la advertencia (UC-06, flujo 4a)"
CODIGO = APU_TUBERIA.codigo_partida
SEGUNDO_RENDIMIENTO = Decimal("110")
FUERA_DE_RANGO = "150"
DENTRO_DEL_RANGO = "105"
CONDICIONES = "condiciones de prueba de C6 (INV-093): no proviene de una ejecucion medida"
JUSTIFICACION = "cuadrilla reforzada en la prueba de C6; texto de prueba, no de obra"


def _base(tmp_path: Path) -> Path:
    """Linea base sembrada y un segundo rendimiento estimado de la tuberia: dos observaciones."""
    base = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            registrar_rendimiento(
                sesion,
                CODIGO,
                SEGUNDO_RENDIMIENTO,
                TipoRendimiento.ESTIMADO,
                FECHA_LINEA_BASE,
                condiciones="segundo estimado de prueba (C6)",
            )
            sesion.commit()
    finally:
        motor.dispose()
    assert [valor for _id, valor, _tipo in _rendimientos(base)] == [
        APU_TUBERIA.rendimiento,
        SEGUNDO_RENDIMIENTO,
    ]
    return base


def _en_base(base: Path, consulta):
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return consulta(sesion)
    finally:
        motor.dispose()


def _rendimientos(base: Path) -> list[tuple[int, Decimal, str]]:
    """(id, valor, tipo) de los rendimientos de la tuberia, por id."""
    return _en_base(
        base,
        lambda s: [
            (fila.id, fila.valor, fila.tipo)
            for fila in s.scalars(
                select(models.Rendimiento)
                .join(models.Partida)
                .where(models.Partida.codigo == CODIGO)
                .order_by(models.Rendimiento.id)
            )
        ],
    )


def _justificaciones(base: Path) -> list[tuple[int, str, str, date]]:
    return _en_base(
        base,
        lambda s: [
            (j.rendimiento_id, j.texto, j.advertencia, j.fecha)
            for j in s.scalars(select(models.JustificacionRendimiento))
        ],
    )


def _contar_justificaciones(base: Path) -> int:
    return _en_base(
        base,
        lambda s: s.scalar(select(func.count()).select_from(models.JustificacionRendimiento)),
    )


def _por_rotulo(elementos, rotulo: str):
    return next(e for e in elementos if e.label == rotulo)


def _hay(elementos, rotulo: str) -> bool:
    return any(e.label == rotulo for e in elementos)


def _pantalla(monkeypatch, base: Path, rendimiento: str) -> AppTest:
    """La partida existente tecleada (sus tablas se precargan), con `rendimiento` y condiciones."""
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.componer")
    monkeypatch.setattr(pagina, "sugerir_partidas_similares", lambda *_: Propuesta(()))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.run()
    _por_rotulo(at.text_input, "Codigo").set_value(CODIGO)
    _por_rotulo(at.text_input, "Descripcion").set_value(APU_TUBERIA.descripcion)
    _por_rotulo(at.text_input, "Unidad").set_value(APU_TUBERIA.unidad)
    at.run()
    # Un rerun de asiento: la precarga del rendimiento cambia el identificador de su campo (ver
    # test_guardar_dos_veces_edita_la_partida en tests/unit/test_ui_componer.py).
    at.run()
    _por_rotulo(at.text_input, pagina.RENDIMIENTO_ETIQUETA).set_value(rendimiento)
    at.text_area[0].set_value(CONDICIONES)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _guardar(at: AppTest) -> None:
    _por_rotulo(at.button, "Guardar composicion").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def _textos(elementos) -> str:
    return "\n".join(str(e.value) for e in elementos)


def test_con_advertencia_la_justificacion_se_liga_al_rendimiento_que_registra_el_guardado(
    monkeypatch, tmp_path
):
    base = _base(tmp_path)
    antes = huella(RUTA_BASE_REAL)

    at = _pantalla(monkeypatch, base, FUERA_DE_RANGO)
    assert "se aparta" in _textos(at.warning)
    _por_rotulo(at.text_input, ROTULO_JUSTIFICACION).set_value(JUSTIFICACION)
    at.run()
    _guardar(at)

    rendimientos = _rendimientos(base)
    assert len(rendimientos) == 3, "el guardado registra el rendimiento nuevo"
    nuevo_id, nuevo_valor, nuevo_tipo = rendimientos[-1]
    assert nuevo_valor == Decimal(FUERA_DE_RANGO)
    assert nuevo_tipo == TipoRendimiento.ESTIMADO.value
    [(rendimiento_id, texto, advertencia, fecha)] = _justificaciones(base)
    assert rendimiento_id == nuevo_id
    assert texto == JUSTIFICACION
    assert "se aparta" in advertencia and FUERA_DE_RANGO in advertencia
    assert "2 observaciones" in advertencia
    assert fecha == date.today(), "la fecha de la cabecera, la misma del rendimiento"
    # U-1: la pantalla es la unica evidencia que tiene el proyectista de que el paso ocurrio.
    exito = _textos(at.success)
    assert "Justificacion de la advertencia registrada" in exito
    assert f"rendimiento {FUERA_DE_RANGO}" in exito
    assert huella(RUTA_BASE_REAL) == antes


def test_sin_advertencia_no_hay_campo_ni_justificacion(monkeypatch, tmp_path):
    base = _base(tmp_path)

    at = _pantalla(monkeypatch, base, DENTRO_DEL_RANGO)
    assert "se aparta" not in _textos(at.warning)
    assert not _hay(at.text_input, ROTULO_JUSTIFICACION)
    _guardar(at)

    assert [valor for _id, valor, _tipo in _rendimientos(base)][-1] == Decimal(DENTRO_DEL_RANGO)
    assert _contar_justificaciones(base) == 0


def test_con_advertencia_y_sin_texto_guarda_sin_justificacion(monkeypatch, tmp_path):
    """La advertencia informa, nunca impide (RF-27): sin texto se guarda igual y se dice."""
    base = _base(tmp_path)

    at = _pantalla(monkeypatch, base, FUERA_DE_RANGO)
    assert _hay(at.text_input, ROTULO_JUSTIFICACION)
    _guardar(at)

    assert [valor for _id, valor, _tipo in _rendimientos(base)][-1] == Decimal(FUERA_DE_RANGO)
    assert _contar_justificaciones(base) == 0
    assert "sin justificacion" in _textos(at.info)
    assert "Justificacion de la advertencia registrada" not in _textos(at.success)


def test_si_el_guardado_no_registra_rendimiento_no_justifica_el_ultimo_y_avisa(
    monkeypatch, tmp_path
):
    """N-5: un guardado que no registra rendimiento (aqui, un doble de `guardar_composicion` que
    no escribe) deja como ultimo el estimado de 110; justificar lo ligaria a el en silencio."""
    base = _base(tmp_path)
    ultimo_antes = _rendimientos(base)[-1]
    pagina = importlib.import_module("ui.paginas.componer")
    monkeypatch.setattr(
        pagina,
        "guardar_composicion",
        lambda _catalogo, composicion, *_: Guardado(resultado=desglose(composicion)),
    )

    at = _pantalla(monkeypatch, base, FUERA_DE_RANGO)
    _por_rotulo(at.text_input, ROTULO_JUSTIFICACION).set_value(JUSTIFICACION)
    at.run()
    _guardar(at)

    assert _rendimientos(base)[-1] == ultimo_antes
    assert _contar_justificaciones(base) == 0
    assert "no registro un rendimiento nuevo" in _textos(at.warning)
