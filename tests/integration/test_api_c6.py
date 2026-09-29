"""Los cinco en duda de GC5 por HTTP (fase C6, pista A): los llamadores de la API del nucleo de C6.

- INV-093 (UC-06 4a): `POST /partidas/{codigo}/rendimientos` registra la justificacion de la
  advertencia de RF-27, solo si hubo advertencia, ligada al rendimiento de esa misma peticion.
- INV-090 (UC-02 2a y 2b): `POST /listas-precios` da de alta los desconocidos elegidos y reporta
  aparte los ignorados (2a) y los rechazados por unidad (2b).
- INV-086 (UC-01 1): `POST /proyectos` crea el proyecto sobre el que luego se elabora.
- INV-076 (RF-24, UC-05 1 y 2): `POST /presupuestos/importar` importa el XLSX de un tercero, lo
  audita y lo persiste; el informe y el libro salen por los `GET` que ya existian.
- INV-099 (UC-07 5): la actualizacion de precios pasa el detector de `ml.anomaly` al nucleo y los
  atipicos salen en el informe de la version revalorada.

Oraculos independientes de la ruta: la linea base (`tests/fixtures/apu_linea_base.py`), las siete
inconsistencias documentadas (`INCONSISTENCIAS`), el presupuesto del tercero de la fixture tabular,
las variaciones de la muestra de UC-02 calculadas a mano (`tests/fixtures/actualizacion_uc02.py`)
y la base leida directamente con SQLAlchemy. La base vive en memoria (fixture `cliente`) y los
archivos en `tmp_path`: nada escribe en `data/`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from tests.fixtures import apu_linea_base as linea_base


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


# ---------------------------------------------------------------------------------------------
# INV-093 (UC-06 4a): la justificacion de la advertencia de rendimiento
# ---------------------------------------------------------------------------------------------

EXCAVACION = linea_base.APU_EXCAVACION.codigo_partida
RUTA_RENDIMIENTOS = f"/partidas/{EXCAVACION}/rendimientos"
JUSTIFICACION = "terreno rocoso en la zanja norte: se excava con martillo"


def _registrar(cliente, valor: str, fecha: str = "2026-07-01", **extra):
    cuerpo = {"valor": valor, "tipo": "estimado", "fecha": fecha, **extra}
    return cliente.post(RUTA_RENDIMIENTOS, json=cuerpo)


def _justificaciones(sesion) -> list[tuple[Decimal, str, str, date]]:
    """(valor del rendimiento, texto, advertencia, fecha) de cada justificacion en la base."""
    consulta = select(
        models.Rendimiento.valor,
        models.JustificacionRendimiento.texto,
        models.JustificacionRendimiento.advertencia,
        models.JustificacionRendimiento.fecha,
    ).join(
        models.JustificacionRendimiento,
        models.JustificacionRendimiento.rendimiento_id == models.Rendimiento.id,
    )
    return [tuple(fila) for fila in sesion.execute(consulta)]


def test_la_justificacion_con_advertencia_queda_ligada_al_rendimiento_registrado(cliente, sesion):
    """UC-06 4a: con advertencia, la justificacion se guarda junto al rendimiento de la peticion."""
    assert _registrar(cliente, "75").status_code == 201  # rango observado: [75, 80]

    r = _registrar(cliente, "300", fecha="2026-07-05", justificacion=JUSTIFICACION)

    assert r.status_code == 201  # advertir nunca es impedir
    cuerpo = r.json()
    assert cuerpo["advertencia"] is not None and "rango" in cuerpo["advertencia"]
    assert cuerpo["justificacion"] == JUSTIFICACION
    assert _justificaciones(sesion) == [
        (Decimal("300"), JUSTIFICACION, cuerpo["advertencia"], date(2026, 7, 5))
    ]


def test_cada_peticion_justifica_su_propio_rendimiento(cliente, sesion):
    """Dos advertencias seguidas: cada justificacion va al rendimiento de su peticion, no a otro."""
    _registrar(cliente, "75")
    primera = _registrar(cliente, "300", fecha="2026-07-05", justificacion="primera")
    segunda = _registrar(cliente, "10", fecha="2026-07-06", justificacion="segunda")

    assert primera.status_code == segunda.status_code == 201
    assert segunda.json()["advertencia"] is not None
    assert [(valor, texto) for valor, texto, _, _ in _justificaciones(sesion)] == [
        (Decimal("300"), "primera"),
        (Decimal("10"), "segunda"),
    ]


def test_la_justificacion_sin_advertencia_se_ignora_y_el_registro_se_hace(cliente, sesion):
    """Sin advertencia no hay nada que justificar: se registra el rendimiento, no la justificacion
    (decision de la pista A: ignorarla, no 422, porque el cliente no sabe de antemano si habra
    advertencia y un 422 impediria un registro que RF-27 no impide)."""
    r = _registrar(cliente, "75", justificacion=JUSTIFICACION)

    assert r.status_code == 201
    assert r.json()["advertencia"] is None
    assert r.json()["justificacion"] is None
    assert _justificaciones(sesion) == []
    historico = cliente.get(RUTA_RENDIMIENTOS).json()["historico"]
    assert [h["valor"] for h in historico][-1] == "75"


@pytest.mark.parametrize("texto", ["", "   "])
def test_una_justificacion_en_blanco_es_422_sin_registrar_nada(cliente, sesion, texto):
    _registrar(cliente, "75")
    antes = _contar(sesion, models.Rendimiento)

    r = _registrar(cliente, "300", fecha="2026-07-05", justificacion=texto)

    assert r.status_code == 422
    assert "justificacion" in r.json()["detalle"]
    assert _contar(sesion, models.Rendimiento) == antes
    assert _justificaciones(sesion) == []


def test_sin_justificacion_la_respuesta_la_trae_nula(cliente, sesion):
    _registrar(cliente, "75")
    r = _registrar(cliente, "300", fecha="2026-07-05")

    assert r.status_code == 201
    assert r.json()["advertencia"] is not None
    assert r.json()["justificacion"] is None
    assert _justificaciones(sesion) == []
