"""UC-06 por HTTP (Sesion I6.2): ejecuciones y rendimientos auditables en la API.

RF-25/26/27 sobre `api/rutas/rendimientos.py`: registrar obras ejecutadas, registrar rendimientos
(estimados y medidos, siempre distinguidos: metas M3 y M4 de `scripts/meta_i6.py`), consultar el
historico con su dispersion y su propuesta, y recibir la advertencia de RF-27 **sin que el
registro se impida**. Montos como texto exacto, como en toda la API (regla 3 de CLAUDE.md).

El fixture `cliente` es el mismo de `tests/integration/test_api.py`: la base en memoria sembrada
deja un rendimiento estimado de 80 m3/dia en LB-01-EXC.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.fixtures import apu_linea_base as linea_base

EXCAVACION = linea_base.APU_EXCAVACION.codigo_partida
SEMBRADO = linea_base.APU_EXCAVACION.rendimiento
RUTA_RENDIMIENTOS = f"/partidas/{EXCAVACION}/rendimientos"


@pytest.fixture
def cliente(sesion):
    from api.dependencias import sesion_api
    from api.main import app

    app.dependency_overrides[sesion_api] = lambda: sesion
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _registrar(cliente: TestClient, valor: str, **extra) -> object:
    cuerpo = {"valor": valor, "tipo": "estimado", "fecha": "2026-07-01", **extra}
    return cliente.post(RUTA_RENDIMIENTOS, json=cuerpo)


def _registrar_ejecucion(cliente: TestClient, referencia: str = "OBRA-2026-01") -> object:
    return cliente.post(
        "/ejecuciones",
        json={
            "referencia": referencia,
            "fecha_inicio": "2026-06-15",
            "descripcion": "Drenaje de la clinica, zanja norte",
        },
    )


def test_ejecucion_se_registra_se_lista_y_no_se_duplica(cliente):
    r = _registrar_ejecucion(cliente)
    assert r.status_code == 201
    assert r.json()["referencia"] == "OBRA-2026-01"

    listado = cliente.get("/ejecuciones")
    assert listado.status_code == 200
    assert [e["referencia"] for e in listado.json()] == ["OBRA-2026-01"]

    assert _registrar_ejecucion(cliente).status_code == 422  # referencia unica


def test_registrar_estimado_devuelve_el_valor_como_texto_exacto(cliente):
    r = _registrar(cliente, "75")
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["rendimiento"]["valor"] == "75"  # str exacto, jamas 75.0
    assert cuerpo["rendimiento"]["tipo"] == "estimado"
    assert cuerpo["rendimiento"]["referencia_ejecucion"] is None
    # Una sola observacion previa (la sembrada) no es comportamiento del cual apartarse.
    assert cuerpo["advertencia"] is None


def test_medido_sin_referencia_es_422_y_con_referencia_real_queda_trazado(cliente):
    sin_referencia = _registrar(cliente, "72", tipo="medido")
    assert sin_referencia.status_code == 422
    assert "MEDIDO" in sin_referencia.json()["detalle"]

    fantasma = _registrar(cliente, "72", tipo="medido", referencia_ejecucion="OBRA-FANTASMA")
    assert fantasma.status_code == 404

    _registrar_ejecucion(cliente)
    r = _registrar(cliente, "72", tipo="medido", referencia_ejecucion="OBRA-2026-01")
    assert r.status_code == 201
    assert r.json()["rendimiento"]["tipo"] == "medido"
    assert r.json()["rendimiento"]["referencia_ejecucion"] == "OBRA-2026-01"


def test_advertencia_fuera_del_rango_observado_sin_impedir_el_registro(cliente):
    """RF-27 completo por HTTP: advertencia con el rango citado y el registro persiste igual."""
    assert _registrar(cliente, "75").status_code == 201  # rango observado: [75, 80]

    r = _registrar(cliente, "300", fecha="2026-07-05")
    assert r.status_code == 201  # advertir nunca es impedir
    advertencia = r.json()["advertencia"]
    assert advertencia is not None and "rango" in advertencia and "75" in advertencia

    historico = cliente.get(RUTA_RENDIMIENTOS).json()["historico"]
    assert [h["valor"] for h in historico][-1] == "300"  # quedo registrado


def test_dentro_del_rango_observado_no_hay_advertencia(cliente):
    _registrar(cliente, "75")
    r = _registrar(cliente, "78", fecha="2026-07-05")
    assert r.status_code == 201 and r.json()["advertencia"] is None


def test_get_trae_historico_dispersion_y_propuesta(cliente):
    _registrar_ejecucion(cliente)
    _registrar(cliente, "75")
    _registrar(
        cliente, "85", tipo="medido", fecha="2026-07-02", referencia_ejecucion="OBRA-2026-01"
    )

    r = cliente.get(RUTA_RENDIMIENTOS)
    assert r.status_code == 200
    cuerpo = r.json()

    assert len(cuerpo["historico"]) == 3  # el 80 sembrado + 75 + 85
    tipos = {h["tipo"] for h in cuerpo["historico"]}
    assert tipos == {"estimado", "medido"}  # siempre distinguidos (M4)

    dispersion = cuerpo["dispersion"]
    assert dispersion["observaciones"] == 3
    assert dispersion["media"] == str((SEMBRADO + Decimal("75") + Decimal("85")) / 3)
    assert dispersion["minimo"] == "75" and dispersion["maximo"] == "85"
    assert dispersion["medidos"] == 1 and dispersion["estimados"] == 2

    propuesta = cuerpo["propuesta"]
    assert propuesta["rendimiento"]["tipo"] == "medido"  # lo observado pesa mas
    assert propuesta["rendimiento"]["valor"] == "85"


def test_partida_desconocida_es_404_y_entradas_invalidas_422(cliente):
    assert cliente.get("/partidas/NO-EXISTE/rendimientos").status_code == 404
    assert _registrar(cliente, "7,5").status_code == 422  # coma decimal: malformado
    assert _registrar(cliente, "-3").status_code == 422  # el contrato exige > 0
    assert _registrar(cliente, "75", tipo="adivinado").status_code == 422  # tipo desconocido
